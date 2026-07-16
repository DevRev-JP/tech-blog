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
from app.shared import confirm_block, narrate, ollama_available  # noqa: E402

DEFAULT_QIDS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]

_Q_NARRATE: dict[str, list[str]] = {
    "Q1": [
        "チケットから製品・顧客を辿ります。",
        "A は断片ごとの粒度差、B はグラフで顧客名を確定します。",
    ],
    "Q2": [
        "Slack とメールは同じ顧客かを聞きます。",
        "A では Markdown の断片だけを渡します（同一を示す関係がありません）。",
        "B では Neo4j の同一顧客関係だけを渡します。",
    ],
    "Q3": [
        "権限の弱いエージェントが、このチケットを見てよいかを聞きます。",
        "A では Markdown にチケット内容が混ざるので、見てよいように答えがちです。",
        "B では閲覧権限の線が無ければ、本文自体を渡しません。",
    ],
    "Q4": [
        "ログ基盤障害の影響範囲を聞きます。",
        "A は叙述のメモ、B は依存関係を辿った結果を渡します。",
    ],
    "Q5": [
        "意味の近さで過去障害を探します。",
        "A はキーワード断片、B はベクトル検索、C は Neo4j のキーワードだけです。",
    ],
    "Q6": [
        "過去30日の P0 件数トップ製品を聞きます。",
        "A は感想だけのメモ、B は SQLite の集計、C は全部 Neo4j に押し込んだ場合です。",
    ],
    "Q7": [
        "P0 に昇格する30分前に何が起きたかを聞きます。",
        "A の Markdown には時刻のつながりがありません。",
        "B では Neo4j 上のイベントの前後関係を渡します。",
    ],
    "Q8": [
        "答えを出す前に、エージェントに見せてよい範囲を聞きます。",
        "A はメモ断片の名前が並ぶだけ、B ではスコープでエンティティが固定されています。",
    ],
}


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
    narrate(
        [
            "同じ問いを、AI に渡す情報だけ変えて聞きます。",
            "先に情報を集め、どのグラフが効くかを表示し、最後に Ollama が答えます。",
            "類似障害と件数集計の問いでは、全部 Neo4j に入れた場合（C）も比べます。",
        ]
    )
    if not ollama_available():
        print("※ Ollama 未起動 — コンテキストの差は表示、LLM 回答はスキップ")
        print("  ollama serve && ollama pull gemma2:2b\n")

    for qid in args.qids:
        q = QUESTIONS[qid]
        print("=" * 60)
        print(f"{qid}: {q}")
        if qid in _Q_NARRATE:
            narrate(_Q_NARRATE[qid])

        file_state = run_agent("file", qid, q)
        _print_run("A. MD断片を読む AI", file_state)

        routed_state = run_agent("routed", qid, q)
        _print_run("B. グラフ（層分離）を読む AI", routed_state)

        if qid in ("Q5", "Q6"):
            narrate(
                [
                    "同じ問いを Neo4j だけから取った場合（C）を見ます。",
                    "B（層を分けた場合）と比べて、渡す事実や答えが弱くなっていれば成功です。",
                ]
            )
            neo_state = run_agent("neo4j_only", qid, q)
            _print_run("C. グラフ1つ(Neo4j)を読む AI", neo_state)

    confirm_block(
        "agent",
        [
            "LangGraph が retrieve_context → route_layer → generate の順で動いている",
            "Q1: MD では顧客が断片ごとにブレる / グラフは関係を辿って確定",
            "Q2: MD では別チャネル＝別顧客と誤認 / グラフは SAME_AS で同顧客",
            "Q3: MD では権限の型がなく秘匿が漏れうる / グラフは CAN_READ で遮断",
            "Q4: MD は叙述 / グラフは BLOCKS で影響範囲を辿る",
            "Q5: Neo4j 単体はキーワードだけ / Qdrant 分離で過去障害を拾える",
            "Q6: Neo4j 単体では集計がずれる / SQLite 分離で audit_log が正確",
            "Q7: MD では時系列を持てない / グラフは Event + BEFORE で30分前が辿れる",
            "Q8: 見せてよいエンティティをスコープで固定できる",
        ],
    )


if __name__ == "__main__":
    main()
