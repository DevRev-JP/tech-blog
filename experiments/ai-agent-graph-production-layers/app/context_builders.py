"""AI に渡すコンテキストを組み立てる（MD 断片 vs グラフ構造）."""

from __future__ import annotations

import json

from app.answer_paths import (
    answer_neo4j_only,
    answer_routed,
)
from app.shared import DATA_DIR, load_json

ContextKind = str  # markdown_fragments | graph_neo4j | graph_routed


def _fragments_markdown() -> str:
    frags = load_json(DATA_DIR / "fragments.json")
    lines = ["# 障害対応メモ（Markdown / JSON 断片）", ""]
    for f in frags:
        lines.append(f"## [{f['source']}]")
        lines.append(f["text"])
        lines.append("")
    return "\n".join(lines)


def _format_graph_facts(title: str, facts: list[str]) -> str:
    lines = [f"# {title}", "", "以下だけを根拠に答えてください。Edge の型を尊重してください。", ""]
    lines.extend(facts)
    return "\n".join(lines)


def build_file_context(qid: str) -> tuple[str, ContextKind, str]:
    """ファイル: AI は MD 断片をそのまま読む（Edge 型なし）."""
    md = _fragments_markdown()
    note = ""
    if qid == "Q3":
        note = (
            "\n（補足: 質問者は agent_guest。断片には CAN_READ の型がないため、"
            "秘匿かどうかはこの叙述からは判定できません）\n"
        )
    body = (
        f"{md}{note}\n---\n"
        f"## 質問\n{qid} に関連しそうな記述を上から探して答えてください。\n"
        f"（注意: 断片には Edge 型がありません）\n"
    )
    return body, "markdown_fragments", ""


def build_neo4j_only_context(qid: str) -> tuple[str, ContextKind, str]:
    """全部 Neo4j から取る想定（層分離なし）."""
    facts: list[str] = []
    route = "Neo4j のみ"

    if qid == "Q1":
        v = answer_neo4j_only(qid).value
        facts = [
            f"(Issue {{id:{v['issue']}}})-[:AFFECTS]->(Product {{name:{v['product']}}})",
            f"(Product)-[:OWNED_BY]->(Customer {{name:{v['customer']}}})",
        ]
    elif qid == "Q2":
        v = answer_neo4j_only(qid).value
        ch = v.get("channels", {})
        facts = [f"(ChannelAccount)-[:SAME_AS]->(Customer {{name:{name}}})" for name in ch.values()]
        route = "Neo4j SAME_AS"
    elif qid == "Q5":
        ids = answer_neo4j_only(qid).value
        facts = [f"(Issue {{id:{i}}})  ※キーワード一致のみ。ベクトル層なし" for i in ids]
        route = "Neo4j Issue キーワード検索"
    elif qid == "Q6":
        v = answer_neo4j_only(qid).value
        neo = v.get("neo4j_issue_severity", [])
        facts = [
            "※ Issue.severity で集計（監査ログではない）",
            *[f"(Product {{name:{r['product']}}}) P0 count={r['p0_count']}" for r in neo],
        ]
        route = "Neo4j Cypher 集計（audit と乖離しうる）"
    elif qid == "Q7":
        v = answer_neo4j_only(qid).value
        facts = [f"escalated_at: {v.get('escalated_at')}"]
        for e in v.get("within_30min_before", []):
            facts.append(f"(Event {{id:{e['id']}}})-[:BEFORE]-> ... at={e['at']} name={e['name']}")
        route = "Neo4j Event 鎖"
    else:
        r = answer_neo4j_only(qid)
        facts = [json.dumps(r.value, ensure_ascii=False)]
        route = "Neo4j"

    return _format_graph_facts("グラフコンテキスト（Neo4j 単体）", facts), "graph_neo4j", route


def build_routed_context(qid: str) -> tuple[str, ContextKind, str]:
    """問いごとに層を分け、グラフとして AI に渡す."""
    facts: list[str] = []
    route = ""

    if qid == "Q1":
        v = answer_routed(qid).value
        facts = [
            f"(Issue {{id:{v['issue']}}})-[:AFFECTS]->(Product {{name:{v['product']}}})",
            f"(Product)-[:OWNED_BY]->(Customer {{name:{v['customer']}}})",
        ]
        route = "Neo4j KG traversal"
    elif qid == "Q2":
        v = answer_routed(qid).value
        for cid, name in v.get("channels", {}).items():
            facts.append(f"(ChannelAccount {{id:{cid}}})-[:SAME_AS]->(Customer {{name:{name}}})")
        if v.get("same_customer"):
            facts.append(f"→ Slack とメールは SAME_AS で同一顧客（{v.get('customer')}）に繋がる")
        else:
            facts.append("→ Slack とメールは別の顧客に繋がる")
        route = "Neo4j SAME_AS"
    elif qid == "Q3":
        allowed = answer_routed(qid).value
        if allowed:
            facts = [
                "(Agent {id:agent_guest})-[:CAN_READ]->(Issue {id:INC-001})",
                "→ agent_guest は INC-001 を閲覧してよい",
            ]
        else:
            facts = [
                "agent_guest から INC-001 への CAN_READ Edge は存在しない",
                "→ agent_guest には INC-001 を閲覧する権限がない（本文は渡さない）",
            ]
        route = "Neo4j CAN_READ traversal"
    elif qid == "Q5":
        hits = answer_routed(qid).value
        facts = [f"(SimilarIncident {{id:{i}}})  ※Qdrant 意味的類似" for i in hits]
        route = "Qdrant vector search"
    elif qid == "Q6":
        rows = answer_routed(qid).value
        facts = [
            "※ SQLite audit_log 集計（昇格イベント）",
            *[f"product={r['product']} P0_escalations={r['p0_count']}" for r in rows],
        ]
        route = "SQLite GROUP BY"
    elif qid == "Q7":
        v = answer_routed(qid).value
        esc = v.get("escalated_at")
        facts.append(f"(Issue)-[:ESCALATED_AT]->(Event) at={esc}")
        before = [e for e in v.get("within_30min_before", []) if e.get("at") != esc]
        for e in before:
            facts.append(f"(Event)-[:BEFORE]->(escalation)  {e['at']}  {e['name']}")
        names = "、".join(e["name"] for e in before) or "（該当なし）"
        facts.append(f"→ P0 昇格（{esc}）の30分前に起きたのは: {names}")
        route = "Neo4j Event + BEFORE"
    else:
        r = answer_routed(qid)
        facts = [json.dumps(r.value, ensure_ascii=False)]
        route = r.reason

    return _format_graph_facts("グラフコンテキスト（層分離）", facts), "graph_routed", route


def build_context(mode: str, qid: str) -> tuple[str, ContextKind, str]:
    if mode == "file":
        return build_file_context(qid)
    if mode == "neo4j_only":
        return build_neo4j_only_context(qid)
    if mode == "routed":
        return build_routed_context(qid)
    raise ValueError(mode)
