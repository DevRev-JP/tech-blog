"""Part2: Graphiti ingest 後の時系列 SSOT 適用と as-of クエリ."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class TemporalEdge:
    fact: str
    valid_at: datetime | None
    invalid_at: datetime | None
    name: str = ""
    source_description: str = ""


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def coerce_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if hasattr(value, "to_native"):
        native = value.to_native()
        if isinstance(native, datetime):
            return native if native.tzinfo else native.replace(tzinfo=timezone.utc)
    return None


def is_active_at(edge: TemporalEdge, as_of: datetime) -> bool:
    valid_at = edge.valid_at
    invalid_at = edge.invalid_at
    if valid_at and valid_at > as_of:
        return False
    if invalid_at and invalid_at <= as_of:
        return False
    return True


def is_invalidated_at(edge: TemporalEdge, as_of: datetime) -> bool:
    """as_of 時点で invalid_at により失効したファクトか."""
    return edge.invalid_at is not None and edge.invalid_at <= as_of


def display_fact(edge: TemporalEdge, cfg: dict) -> str:
    """SSOT の canonical_fact があれば表示・dedupe 用にそれを使う."""
    rule = rule_for_fact(edge.fact, cfg)
    if rule and rule.get("canonical_fact"):
        return rule["canonical_fact"]
    return edge.fact


def dedupe_edges(edges: list[TemporalEdge], cfg: dict) -> list[TemporalEdge]:
    """同一 canonical 文言の重複 edge を 1 件にまとめる（SSOT / valid_at 優先）."""
    best: dict[str, TemporalEdge] = {}
    for edge in edges:
        key = display_fact(edge, cfg)
        prev = best.get(key)
        if prev is None:
            best[key] = edge
            continue
        if edge.name == "DEMO_SSOT" and prev.name != "DEMO_SSOT":
            best[key] = edge
        elif edge.valid_at and not prev.valid_at:
            best[key] = edge
    return list(best.values())


def _matches_rule(fact: str, rule: dict) -> bool:
    needles = rule.get("match_any") or [rule.get("match_contains", "")]
    return any(n and n in fact for n in needles)


def _ensure_canonical_fact(session, rule: dict) -> bool:
    """Graphiti 抽出に 500/800 等が無いとき、SSOT 文言のファクトを MERGE する."""
    fact = rule.get("canonical_fact")
    rule_id = rule.get("id")
    if not fact or not rule_id:
        return False

    valid_at = parse_dt(rule["valid_at"])
    invalid_at = parse_dt(rule.get("invalid_at"))
    edge_uuid = f"demo-ssot-{rule_id}"
    source_uuid = f"demo-ssot-src-{rule_id}"
    target_uuid = f"demo-ssot-tgt-{rule_id}"
    now = datetime.now(timezone.utc).isoformat()

    session.run(
        """
        MERGE (s:Entity {uuid: $source_uuid})
        ON CREATE SET s.name = '顧客X', s.group_id = '', s.created_at = datetime($now)
        MERGE (t:Entity {uuid: $target_uuid})
        ON CREATE SET t.name = 'DemoFact', t.group_id = '', t.created_at = datetime($now)
        MERGE (s)-[e:RELATES_TO {uuid: $edge_uuid}]->(t)
        SET e.fact = $fact,
            e.name = 'DEMO_SSOT',
            e.group_id = '',
            e.created_at = coalesce(e.created_at, datetime($now)),
            e.valid_at = datetime($valid_at),
            e.invalid_at = CASE
                WHEN $invalid_at IS NULL THEN NULL
                ELSE datetime($invalid_at)
            END
        """,
        source_uuid=source_uuid,
        target_uuid=target_uuid,
        edge_uuid=edge_uuid,
        fact=fact,
        valid_at=valid_at.isoformat() if valid_at else None,
        invalid_at=invalid_at.isoformat() if invalid_at else None,
        now=now,
    )
    return True


def repair_temporal_facts(driver, cfg: dict) -> list[str]:
    """Graphiti が付け損ねた valid_at / invalid_at を SSOT ルールで上書きする."""
    rules = cfg.get("temporal_rules") or []
    logs: list[str] = []

    with driver.session() as session:
        for rule in rules:
            needles = [n for n in (rule.get("match_any") or [rule.get("match_contains")]) if n]
            if not needles:
                continue

            valid_at = parse_dt(rule["valid_at"])
            invalid_at = parse_dt(rule.get("invalid_at"))
            valid_iso = valid_at.isoformat() if valid_at else None
            invalid_iso = invalid_at.isoformat() if invalid_at else None

            canonical = rule.get("canonical_fact")
            result = session.run(
                """
                MATCH ()-[e:RELATES_TO]->()
                WHERE ANY(n IN $needles WHERE e.fact CONTAINS n)
                SET e.fact = CASE
                        WHEN $canonical_fact IS NULL THEN e.fact
                        ELSE $canonical_fact
                    END,
                    e.valid_at = CASE WHEN $valid_at IS NULL THEN e.valid_at ELSE datetime($valid_at) END,
                    e.invalid_at = CASE
                        WHEN $invalid_at IS NULL THEN NULL
                        ELSE datetime($invalid_at)
                    END
                RETURN count(e) AS updated
                """,
                needles=needles,
                canonical_fact=canonical,
                valid_at=valid_iso,
                invalid_at=invalid_iso,
            )
            updated = result.single()["updated"]
            label = rule.get("id") or needles[0]
            invalid_label = invalid_iso[:10] if invalid_iso else "現在有効"
            valid_label = valid_iso[:10] if valid_iso else "?"

            if updated == 0 and rule.get("canonical_fact"):
                if _ensure_canonical_fact(session, rule):
                    updated = 1
                    logs.append(
                        f"  - {label}: {updated}件（canonical 追加 — valid {valid_label} 〜 invalid {invalid_label}）"
                    )
                    continue

            logs.append(f"  - {label}: {updated}件（valid {valid_label} 〜 invalid {invalid_label}）")

    return logs


def fetch_temporal_edges(driver, keywords: tuple[str, ...]) -> list[TemporalEdge]:
    with driver.session() as session:
        result = session.run(
            """
            MATCH ()-[e:RELATES_TO]->()
            WHERE ANY(k IN $keywords WHERE e.fact CONTAINS k)
            RETURN e.fact AS fact,
                   e.valid_at AS valid_at,
                   e.invalid_at AS invalid_at,
                   e.name AS name
            ORDER BY e.valid_at, e.fact
            """,
            keywords=list(keywords),
        )
        edges: list[TemporalEdge] = []
        for row in result:
            edges.append(
                TemporalEdge(
                    fact=row["fact"],
                    valid_at=coerce_dt(row["valid_at"]),
                    invalid_at=coerce_dt(row["invalid_at"]),
                    name=row["name"] or "",
                )
            )
        return edges


def rule_for_fact(fact: str, cfg: dict) -> dict | None:
    for rule in cfg.get("temporal_rules") or []:
        if _matches_rule(fact, rule):
            return rule
    return None
