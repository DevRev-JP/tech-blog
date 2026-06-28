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

from shared import (
    DATA_DIR,
    checkpoint,
    create_graphiti_client,
    demo_run_context,
    get_neo4j_driver,
    is_demo_batch,
    is_demo_quiet,
    milestone,
    section,
    step_print,
)
from temporal_graph import (
    TemporalEdge,
    dedupe_edges,
    display_fact,
    fetch_temporal_edges,
    filter_by_persona,
    future_plan_edges,
    is_active_at,
    is_invalidated_at,
    open_conflict_edges,
    parse_dt,
    provenance_label,
    repair_temporal_facts,
    rule_for_fact,
)

SEARCH_KEYWORDS = (
    "予算",
    "800",
    "500",
    "万",
    "Project",
    "Alpha",
    "顧客",
    "3ヶ月",
    "6ヶ月",
    "再稟議",
    "今期",
    "来期",
    "リソース",
    "整合",
    "3人月",
    "拡張",
    "10月",
    "リリース",
)
BUDGET_KEYWORDS = ("予算", "500", "800", "万", "Project", "Alpha", "顧客")


def load_config() -> dict:
    return yaml.safe_load((DATA_DIR / "temporal_episodes.yaml").read_text(encoding="utf-8"))


def resolve_as_of(cfg: dict, as_of_arg: str | None) -> datetime:
    if not as_of_arg:
        return parse_dt(cfg["as_of"]) or datetime.fromisoformat("2026-06-28T12:00:00+09:00")

    presets = cfg.get("as_of_presets") or {}
    if as_of_arg in presets:
        return parse_dt(presets[as_of_arg]) or datetime.fromisoformat("2026-06-28T12:00:00+09:00")

    parsed = parse_dt(as_of_arg)
    if parsed:
        return parsed
    raise ValueError(f"不明な as-of: {as_of_arg}（preset: {', '.join(presets)} または ISO8601）")


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "現在有効"
    return value.strftime("%Y-%m-%d")


def _is_relevant_fact(fact: str) -> bool:
    return any(k in fact for k in SEARCH_KEYWORDS)


def _is_budget_fact(fact: str) -> bool:
    return any(k in fact for k in BUDGET_KEYWORDS)


def _persona_label(cfg: dict, persona: str | None) -> str:
    if not persona:
        return "全体"
    perspectives = cfg.get("perspectives") or {}
    return (perspectives.get(persona) or {}).get("label") or persona


def _has_known_provenance(edge: TemporalEdge, cfg: dict) -> bool:
    return "出所不明" not in provenance_label(edge, cfg)


def _collect_search_edges(
    edges: list[TemporalEdge],
    cfg: dict,
    *,
    as_of: datetime,
    persona: str | None,
    all_edges: list[TemporalEdge] | None = None,
) -> tuple[list[TemporalEdge], list[TemporalEdge]]:
    source_edges = all_edges if all_edges is not None else edges
    edges = filter_by_persona(edges, cfg, persona)
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
    if is_demo_batch() and is_demo_quiet():
        active = [e for e in active if _has_known_provenance(e, cfg)]
    active_labels = {display_fact(edge, cfg) for edge in active}
    excluded = [
        edge
        for edge in dedupe_edges(excluded, cfg)
        if display_fact(edge, cfg) not in active_labels
    ]
    return active, excluded


def format_search_compact(
    edges: list[TemporalEdge],
    cfg: dict,
    *,
    as_of: datetime,
    persona: str | None = None,
    all_edges: list[TemporalEdge] | None = None,
) -> None:
    label = _persona_label(cfg, persona)
    active, excluded = _collect_search_edges(
        edges, cfg, as_of=as_of, persona=persona, all_edges=all_edges
    )
    print(f"\n▸ search  {_fmt_dt(as_of)} · {label}")
    if not active:
        print("  （有効ファクトなし）")
    else:
        for edge in sorted(active, key=lambda e: e.valid_at or datetime.min.replace(tzinfo=as_of.tzinfo)):
            src = provenance_label(edge, cfg).split(" / ")[0]
            print(f"  ・{display_fact(edge, cfg)}")
            print(f"    {_fmt_dt(edge.valid_at)}–{_fmt_dt(edge.invalid_at)} · {src}")

    presets = cfg.get("as_of_presets") or {}
    monday = parse_dt(presets.get("monday"))
    if monday and as_of <= monday:
        print("  → `--as-of today` で800万へ")
    elif excluded:
        sample = excluded[0]
        print(
            f"  → 失効: {display_fact(sample, cfg)}（invalid {_fmt_dt(sample.invalid_at)}）"
        )

    source_edges = all_edges if all_edges is not None else edges
    show_conflicts = persona in (None, "manager", "eng")
    friday = parse_dt(presets.get("friday"))
    if show_conflicts and friday and as_of >= friday:
        conflicts = open_conflict_edges(source_edges, cfg, as_of)
        if conflicts and persona in (None, "eng"):
            print(f"  ⚠ 未解決: {display_fact(conflicts[0], cfg)}")


def format_search_with_provenance(
    edges: list[TemporalEdge],
    cfg: dict,
    *,
    as_of: datetime,
    persona: str | None = None,
    all_edges: list[TemporalEdge] | None = None,
) -> None:
    if is_demo_batch() and is_demo_quiet():
        format_search_compact(
            edges, cfg, as_of=as_of, persona=persona, all_edges=all_edges
        )
        return

    source_edges = all_edges if all_edges is not None else edges
    active, excluded = _collect_search_edges(
        edges, cfg, as_of=as_of, persona=persona, all_edges=all_edges
    )

    persona_note = f" / 視点: {_persona_label(cfg, persona)}" if persona else ""
    section(f"結論（{_fmt_dt(as_of)} 時点で有効なファクト{persona_note}）")
    if not active:
        print("（現在有効なファクトが見つかりませんでした）")
    for edge in sorted(active, key=lambda e: e.valid_at or datetime.min.replace(tzinfo=as_of.tzinfo)):
        print(f"・{display_fact(edge, cfg)}")
        print(f"  valid: {_fmt_dt(edge.valid_at)} 〜 invalid: {_fmt_dt(edge.invalid_at)}")
        print(f"  出所: {provenance_label(edge, cfg)}")

    section("なぜ800万か（グラフの根拠）")
    presets = cfg.get("as_of_presets") or {}
    monday = parse_dt(presets.get("monday"))
    friday = parse_dt(presets.get("friday"))

    budget_pool = filter_by_persona(
        [e for e in source_edges if _is_budget_fact(e.fact)],
        cfg,
        persona if persona != "eng" else "manager",
    )
    active_500 = [e for e in budget_pool if is_active_at(e, as_of) and ("500" in e.fact or "500万" in e.fact)]
    active_800 = [e for e in active if "800" in e.fact or "800万" in e.fact]
    invalidated_500 = [e for e in budget_pool if is_invalidated_at(e, as_of) and ("500" in e.fact or "500万" in e.fact)]

    if monday and as_of <= monday:
        if active_500:
            e = active_500[0]
            print(f"1. {_fmt_dt(e.valid_at)}「{display_fact(e, cfg)}」→ この as-of では有効（月曜時点の正解は500万）")
        print("→ 水曜以降に800万ファクトが有効化。`--as-of today` と比較してください。")
    elif invalidated_500 and active_800:
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
        print("→ 水曜エピソード取込で月曜ファクトが invalid 化。today as-of の正解は800万。")
    else:
        print("（予算ファクトの invalid 化がグラフ上で確認できませんでした — SSOT 適用後に today preset を試してください）")

    show_future = persona in (None, "manager", "eng")
    if show_future and friday and as_of >= friday:
        futures = future_plan_edges(source_edges, cfg, as_of)
        futures = filter_by_persona(futures, cfg, persona)
        if futures:
            section("将来予定（グラフ上の計画 — 未到来のマイルストーン）")
            for edge in futures:
                print(f"・{display_fact(edge, cfg)}")
                print(f"  valid: {_fmt_dt(edge.valid_at)} 〜 invalid: {_fmt_dt(edge.invalid_at)}")
                print(f"  出所: {provenance_label(edge, cfg)}")
            print(
                "→ 10月リリース等の「これから」もファクトとして保持。"
                " `--as-of monday` では木曜エピソード前のため未登場。"
            )

    show_conflicts = persona in (None, "manager", "eng")
    if show_conflicts and friday and as_of >= friday:
        conflicts = open_conflict_edges(source_edges, cfg, as_of)
        if conflicts:
            section("未解決の矛盾（マルチプレイヤー — 営業 vs エンジニア）")
            for edge in conflicts:
                print(f"・{display_fact(edge, cfg)}")
                print(f"  出所: {provenance_label(edge, cfg)}")
            print(
                "→ 営業の800万前提とエンジニア試算が両方グラフに残る。"
                "最新値だけ Skill に書くとこの緊張が消える。"
            )

    if excluded:
        section("検索結果から除外されたもの（invalid_at により失効）")
        for edge in excluded:
            print(
                f"・「{display_fact(edge, cfg)}」— invalid_at: {_fmt_dt(edge.invalid_at)}"
                f"（{provenance_label(edge, cfg)}）"
            )


def _budget_transition_line(cfg: dict) -> str:
    rules = {r["id"]: r for r in cfg.get("temporal_rules") or [] if r.get("id")}
    r500 = rules.get("budget_500", {})
    r800 = rules.get("budget_800", {})
    v500 = parse_dt(r500.get("valid_at"))
    i500 = parse_dt(r500.get("invalid_at"))
    v800 = parse_dt(r800.get("valid_at"))
    if v500 and i500 and v800:
        return (
            f"500万（{v500.strftime('%m/%d')}〜{i500.strftime('%m/%d')}） "
            f"──[営業B・山田部長面談 / sales-update-wednesday]──> "
            f"800万（{v800.strftime('%m/%d')}〜現在）"
        )
    return "500万 → 800万（SSOT temporal_rules 参照）"


def format_history(edges: list[TemporalEdge], cfg: dict, *, as_of: datetime) -> None:
    budget_facts = dedupe_edges([e for e in edges if _is_budget_fact(e.fact)], cfg)
    if is_demo_batch() and is_demo_quiet():
        print(f"\n▸ history  予算変遷（{_fmt_dt(as_of)}）")
        core = [e for e in budget_facts if _has_known_provenance(e, cfg)]
        transition = _budget_transition_line(cfg)
        print(f"  {transition}")
        if core:
            print(f"  関連ファクト {len(core)} 件（詳細: --verbose part2-search today）")
        return

    section("予算の変遷")
    if not budget_facts:
        print("（予算関連ファクトが見つかりませんでした）")
        return

    for edge in sorted(budget_facts, key=lambda e: e.valid_at or datetime.min.replace(tzinfo=as_of.tzinfo)):
        print(f"{display_fact(edge, cfg)}  [{_fmt_dt(edge.valid_at)} 〜 {_fmt_dt(edge.invalid_at)}]")
        print(f"  出所: {provenance_label(edge, cfg)}")

    print()
    print(_budget_transition_line(cfg))
    print("  置換理由: 水曜エピソード取込時に Graphiti が古いファクトを invalid 化")


async def cmd_ingest() -> None:
    cfg = load_config()
    episodes = cfg["episodes"]
    graphiti = create_graphiti_client()
    try:
        if not is_demo_batch():
            step_print(1, 2, f"{len(episodes)}エピソードを Graphiti に取込中（Ollama LLM 使用、数分）…")
        for i, ep in enumerate(episodes, start=1):
            if is_demo_batch() and is_demo_quiet():
                print(f"  [{i}/{len(episodes)}] {ep['name']} …", end="", flush=True)
            elif not is_demo_batch():
                print(f"  - [{i}/{len(episodes)}] {ep['name']}")
            ref = datetime.fromisoformat(ep["reference_time"].replace("Z", "+00:00"))
            await graphiti.add_episode(
                name=ep["name"],
                episode_body=ep["body"].strip(),
                source=EpisodeType.text,
                source_description=ep["source_description"],
                reference_time=ref,
            )
            if is_demo_batch() and is_demo_quiet():
                print(" OK")
    finally:
        await graphiti.close()

    driver = get_neo4j_driver()
    try:
        if not is_demo_batch():
            step_print(2, 2, "時系列 SSOT を適用（invalid_at の確定）…")
        logs = repair_temporal_facts(driver, cfg)
        if is_demo_batch() and is_demo_quiet():
            milestone(
                "ingest + SSOT（budget_500/800, oct_release, eng_budget_conflict）"
            )
        elif logs:
            print("\n".join(logs))
        else:
            print("  （temporal_rules 未定義 — スキップ）")
        if not is_demo_batch():
            section("完了")
            print(f"{len(episodes)}エピソード取込 + 時系列確定完了")
        checkpoint(
            "Part2 ingest",
            [
                "SSOT に budget_500 / budget_800 / oct_release_target / eng_budget_conflict が出ている",
                "次: python app/demo_temporal.py search --as-of monday → today で差を比較",
            ],
        )
    finally:
        driver.close()


async def cmd_search(query: str, as_of_arg: str | None, persona: str | None) -> None:
    _ = query
    cfg = load_config()
    as_of = resolve_as_of(cfg, as_of_arg)
    driver = get_neo4j_driver()
    try:
        label = _persona_label(cfg, persona)
        if not (is_demo_batch() and is_demo_quiet()):
            step_print(
                1,
                1,
                f"search: {cfg['search_queries']['manager_friday']}（as-of {_fmt_dt(as_of)} / {label}）",
            )
        edges = fetch_temporal_edges(driver, SEARCH_KEYWORDS)
        format_search_with_provenance(
            edges,
            cfg,
            as_of=as_of,
            persona=persona,
            all_edges=edges,
        )
    finally:
        driver.close()


async def cmd_history(query: str, as_of_arg: str | None) -> None:
    _ = query
    cfg = load_config()
    as_of = resolve_as_of(cfg, as_of_arg)
    driver = get_neo4j_driver()
    try:
        if not (is_demo_batch() and is_demo_quiet()):
            step_print(1, 1, f"history: {cfg['search_queries']['budget_history']}（as-of {_fmt_dt(as_of)}）")
        edges = fetch_temporal_edges(driver, BUDGET_KEYWORDS)
        format_history(edges, cfg, as_of=as_of)
        if is_demo_batch() and is_demo_quiet():
            return
        section("補足")
        print(
            "Skill に最新値だけ書いても、なぜ500万が無効かはグラフの invalid_at + エピソード出所で説明できます。"
            " `./run_demo.sh part2-search monday` と `today` で as-of の差も比較してください。"
        )
    finally:
        driver.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Graphiti temporal demo")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest")
    p_search = sub.add_parser("search")
    p_search.add_argument("--query", default=None)
    p_search.add_argument(
        "--as-of",
        dest="as_of",
        default=None,
        help="ISO8601 または preset（monday / wednesday / friday / today）",
    )
    p_search.add_argument(
        "--persona",
        choices=["sales", "eng", "manager"],
        default=None,
        help="視点フィルタ（営業 / エンジニア / マネージャー）",
    )
    p_hist = sub.add_parser("history")
    p_hist.add_argument("--query", default=None)
    p_hist.add_argument("--as-of", dest="as_of", default=None)

    args = parser.parse_args()

    with demo_run_context():
        if args.command == "ingest":
            await cmd_ingest()
        elif args.command == "search":
            await cmd_search(args.query, args.as_of, args.persona)
        elif args.command == "history":
            await cmd_history(args.query, args.as_of)


if __name__ == "__main__":
    asyncio.run(main())
