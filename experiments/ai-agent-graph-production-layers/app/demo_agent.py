#!/usr/bin/env python3
"""LangGraph エージェント — MD を読む AI vs グラフを読む AI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent_router import run_agent  # noqa: E402
from app.answer_paths import QUESTIONS  # noqa: E402
from app.shared import confirm_block, ollama_available  # noqa: E402

DEFAULT_QIDS = ["Q6", "Q7", "Q4", "Q1"]


def _print_run(label: str, state: dict) -> None:
    print(f"\n--- {label} ---")
    print(f"読み方: {state.get('context_kind')} / 効くグラフ: {state.get('graph_kind')}")
    print(f"取得経路: {state.get('layer_route')}")
    print("【AI に渡したコンテキスト（先頭400字）】")
    ctx = state.get("context", "")
    print(ctx[:400] + ("..." if len(ctx) > 400 else ""))
    msg = state["messages"][-1].content if state.get("messages") else ""
    print("【AI の回答】")
    print(msg)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qids", nargs="*", default=DEFAULT_QIDS)
    args = parser.parse_args()

    print("LangGraph: retrieve_context → route_layer → generate（Ollama）")
    if not ollama_available():
        print("※ Ollama 未起動 — コンテキストの差は表示、LLM 回答はスキップ")
        print("  ollama serve && ollama pull gemma2:2b\n")

    for qid in args.qids:
        q = QUESTIONS[qid]
        print("=" * 60)
        print(f"{qid}: {q}")

        file_state = run_agent("file", qid, q)
        _print_run("A. MD断片を読む AI（段階0）", file_state)

        routed_state = run_agent("routed", qid, q)
        _print_run("B. グラフ（層分離）を読む AI（段階2）", routed_state)

        if qid in ("Q2", "Q5"):
            neo_state = run_agent("neo4j_only", qid, q)
            _print_run("C. グラフ1つ(Neo4j)を読む AI（段階1）", neo_state)

    confirm_block(
        "agent",
        [
            "LangGraph が retrieve_context → route_layer → generate の順で動いている",
            "Q4: MD では権限の型がなく秘匿が漏れうる / グラフは CAN_READ で遮断",
            "Q6: MD では別チャネル＝別顧客と誤認 / グラフは SAME_AS で同顧客",
            "Q7: MD では時系列を持てない / グラフは Event + BEFORE で30分前が辿れる",
            "MD: 叙述断片を丸ごと渡す → Edge 型なし → 推測しやすい",
            "グラフ: 型付き fact だけ渡す → 根拠が辿れる",
        ],
    )


if __name__ == "__main__":
    main()
