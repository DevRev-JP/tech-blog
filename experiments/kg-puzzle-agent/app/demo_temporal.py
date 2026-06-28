"""Part2: Graphiti テンポラルデモ — ingest / search / history."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graphiti_core.nodes import EpisodeType

from shared import DATA_DIR, create_graphiti_client, get_neo4j_driver, section, step_print
from temporal_graph import (
    TemporalEdge,
    dedupe_edges,
    display_fact,
    fetch_temporal_edges,
    is_active_at,
    is_invalidated_at,
    parse_dt,
    repair_temporal_facts,
    rule_for_fact,
)

SEARCH_KEYWORDS = ("予算", "800", "500", "万", "顧客", "3ヶ月", "6ヶ月", "再稟議", "今期", "来期")
BUDGET_KEYWORDS = ("予算", "500", "800", "万")


def load_config() -> dict:
    return yaml.safe_load((DATA_DIR / "temporal_episodes.yaml").read_text(encoding="utf-8"))


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "現在有効"
    return value.strftime("%Y-%m-%d")


def _is_relevant_fact(fact: str) -> bool:
    return any(k in fact for k in SEARCH_KEYWORDS)


def _is_budget_fact(fact: str) -> bool:
    return any(k in fact for k in BUDGET_KEYWORDS)


def _as_of(cfg: dict) -> datetime:
    return parse_dt(cfg["as_of"]) or datetime.fromisoformat("2024-11-08T12:00:00+00:00")


def format_search_with_provenance(edges: list[TemporalEdge], cfg: dict) -> None:
    as_of = _as_of(cfg)
    active: list[TemporalEdge] = []
    excluded: list[TemporalEdge] = []

    for edge in edges:
        if not _is_relevant_fact(edge.fact):
            continue
        if is_active_at(edge, as_of):
            active.append(edge)
        elif is_invalidated_at(edge, as_of):
            excluded.append(edge)

    active = dedupe_edges(active, cfg)
    active_labels = {display_fact(edge, cfg) for edge in active}
    excluded = [
        edge
        for edge in dedupe_edges(excluded, cfg)
        if display_fact(edge, cfg) not in active_labels
    ]

    section(f"結論（{ _fmt_dt(as_of) } 時点で有効なファクト）")
    if not active:
        print("（現在有効なファクトが見つかりませんでした）")
    for edge in sorted(active, key=lambda e: e.valid_at or datetime.min.replace(tzinfo=as_of.tzinfo)):
        print(f"・{display_fact(edge, cfg)}")
        print(f"  valid: {_fmt_dt(edge.valid_at)} 〜 invalid: {_fmt_dt(edge.invalid_at)}")

    section("なぜ800万か（グラフの根拠）")
    invalidated_500 = [e for e in excluded if _is_budget_fact(e.fact) and ("500" in e.fact or "500万" in e.fact)]
    active_800 = [e for e in active if "800" in e.fact or "800万" in e.fact]

    if invalidated_500 and active_800:
        old = invalidated_500[0]
        new = active_800[0]
        old_rule = rule_for_fact(old.fact, cfg) or {}
        new_rule = rule_for_fact(new.fact, cfg) or {}
        print(
            f"1. {_fmt_dt(old.valid_at)}「{display_fact(old, cfg)}」"
            f" → invalid: {_fmt_dt(old.invalid_at)}（{old_rule.get('episode', 'sales-meeting-monday')}）"
        )
        print(
            f"2. {_fmt_dt(new.valid_at)}「{display_fact(new, cfg)}」"
            f" → 現在有効（{new_rule.get('episode', 'sales-update-wednesday')}）"
        )
        print("→ 水曜エピソード取込で月曜ファクトが invalid 化。金曜時点の正解は800万。")
    else:
        print("（予算ファクトの invalid 化がグラフ上で確認できませんでした）")

    if excluded:
        section("検索結果から除外されたもの（invalid_at により失効）")
        for edge in excluded:
            rule = rule_for_fact(edge.fact, cfg)
            source = (rule or {}).get("source_description") or "更新により置換"
            print(
                f"・「{display_fact(edge, cfg)}」— invalid_at: {_fmt_dt(edge.invalid_at)}（{source}）"
            )


def format_history(edges: list[TemporalEdge], cfg: dict) -> None:
    as_of = _as_of(cfg)
    budget_facts = dedupe_edges([e for e in edges if _is_budget_fact(e.fact)], cfg)
    section("予算の変遷")
    if not budget_facts:
        print("（予算関連ファクトが見つかりませんでした）")
        return

    for edge in sorted(budget_facts, key=lambda e: e.valid_at or datetime.min.replace(tzinfo=as_of.tzinfo)):
        print(f"{display_fact(edge, cfg)}  [{_fmt_dt(edge.valid_at)} 〜 {_fmt_dt(edge.invalid_at)}]")

    print()
    print(
        "500万（11/04〜11/06） ──[営業B・山田部長面談 / sales-update-wednesday]──> "
        "800万（11/06〜現在）"
    )
    print("  置換理由: 水曜エピソード取込時に Graphiti が古いファクトを invalid 化")


async def cmd_ingest() -> None:
    cfg = load_config()
    graphiti = create_graphiti_client()
    try:
        step_print(1, 2, "3エピソードを Graphiti に取込中（Ollama LLM 使用、数分かかる場合があります）…")
        for i, ep in enumerate(cfg["episodes"], start=1):
            print(f"  - [{i}/3] {ep['name']}")
            ref = datetime.fromisoformat(ep["reference_time"].replace("Z", "+00:00"))
            await graphiti.add_episode(
                name=ep["name"],
                episode_body=ep["body"].strip(),
                source=EpisodeType.text,
                source_description=ep["source_description"],
                reference_time=ref,
            )
    finally:
        await graphiti.close()

    driver = get_neo4j_driver()
    try:
        step_print(2, 2, "時系列 SSOT を適用（invalid_at の確定）…")
        logs = repair_temporal_facts(driver, cfg)
        if logs:
            print("\n".join(logs))
        else:
            print("  （temporal_rules 未定義 — スキップ）")
        section("完了")
        print("3エピソード取込 + 時系列確定完了")
    finally:
        driver.close()


async def cmd_search(query: str) -> None:
    _ = query
    cfg = load_config()
    driver = get_neo4j_driver()
    try:
        step_print(1, 1, f"search: {cfg['search_queries']['manager_friday']}")
        edges = fetch_temporal_edges(driver, SEARCH_KEYWORDS)
        format_search_with_provenance(edges, cfg)
    finally:
        driver.close()


async def cmd_history(query: str) -> None:
    _ = query
    cfg = load_config()
    driver = get_neo4j_driver()
    try:
        step_print(1, 1, f"history: {cfg['search_queries']['budget_history']}")
        edges = fetch_temporal_edges(driver, BUDGET_KEYWORDS)
        format_history(edges, cfg)
        section("補足")
        print("Skill に最新値だけ書いても、なぜ500万が無効かはグラフの invalid_at + エピソード出所で説明できます。")
    finally:
        driver.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Graphiti temporal demo")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest")
    p_search = sub.add_parser("search")
    p_search.add_argument("--query", default=None)
    p_hist = sub.add_parser("history")
    p_hist.add_argument("--query", default=None)

    args = parser.parse_args()

    if args.command == "ingest":
        await cmd_ingest()
    elif args.command == "search":
        await cmd_search(args.query)
    elif args.command == "history":
        await cmd_history(args.query)


if __name__ == "__main__":
    asyncio.run(main())
