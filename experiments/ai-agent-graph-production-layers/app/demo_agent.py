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

DEFAULT_QIDS = ["Q6", "Q7", "Q5", "Q4"]

# 各問いの直前に出す「いま何をしているか」
_Q_NARRATE: dict[str, list[str]] = {
    "Q6": [
        "次は同一性の確認です。Slack とメールは同じ顧客か、を聞きます。",
        "A では Markdown の断片だけを渡します（同一を示す線がありません）。",
        "B では Neo4j の「同一顧客」関係だけを渡します。",
        "A が曖昧で、B が「はい」と根拠つきで答えれば成功です。",
    ],
    "Q7": [
        "次は時間軸です。P0 に昇格する30分前に何が起きたかを聞きます。",
        "A の Markdown には時刻のつながりがありません。",
        "B では Neo4j 上のイベントの前後関係を渡します。",
        "B がリリースやレイテンシ悪化などを列挙できれば成功です。",
    ],
    "Q5": [
        "次がタイトルの核心です。過去30日の P0 件数トップ製品を聞きます。",
        "A は感想だけのメモ、B は SQLite の集計、C は全部 Neo4j に押し込んだ場合です。",
        "C が出るのは、類似検索や集計のように「Graph DB だけでは弱い」問いだけです。",
        "B と C で件数や答え方が違えば、「1つの DB だけでは足りない」と分かれば成功です。",
    ],
    "Q4": [
        "次は権限です。権限の弱いエージェントが、このチケットを見てよいかを聞きます。",
        "A では Markdown にチケット内容が混ざるので、見てよいように答えがちです。",
        "B では閲覧権限の線が無ければ、本文自体を渡しません。",
        "A が内容に触れ、B が断定できない（または拒否する）なら成功です。",
    ],
    "Q2": [
        "次は類似障害です。意味の近さで過去障害を探す例です。",
        "A はキーワード断片、B はベクトル検索、C は Neo4j のキーワードだけです。",
        "C が取りこぼし、B が過去の障害 ID を返せば成功です。",
    ],
    "Q1": [
        "次は顧客特定です。チケットから製品・顧客を辿ります。",
        "A は断片ごとの粒度差、B はグラフで顧客名を確定します。",
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
            "同じ問いを、AI に渡す情報だけ変えて何度か聞きます。",
            "先に情報を集め、どのグラフが効くかを表示し、最後に Ollama が答えます。",
            "順番は Q6 → Q7 → Q5 → Q4 です。Q5 だけ、全部 Neo4j に入れた場合（C）も比べます。",
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
        _print_run("A. MD断片を読む AI（段階0）", file_state)

        routed_state = run_agent("routed", qid, q)
        _print_run("B. グラフ（層分離）を読む AI（段階2）", routed_state)

        if qid in ("Q2", "Q5"):
            narrate(
                [
                    "つづいて、同じ問いを Neo4j だけから取った場合（C）を見ます。",
                    "B（層を分けた場合）と比べて、渡す事実や答えが弱くなっていれば成功です。",
                ]
            )
            neo_state = run_agent("neo4j_only", qid, q)
            _print_run("C. グラフ1つ(Neo4j)を読む AI（段階1）", neo_state)

    confirm_block(
        "agent",
        [
            "LangGraph が retrieve_context → route_layer → generate の順で動いている",
            "Q4: MD では権限の型がなく秘匿が漏れうる / グラフは CAN_READ で遮断",
            "Q6: MD では別チャネル＝別顧客と誤認 / グラフは SAME_AS で同顧客",
            "Q7: MD では時系列を持てない / グラフは Event + BEFORE で30分前が辿れる",
            "Q5: Neo4j 単体では集計 fact がずれる / SQLite 分離で audit_log が正確",
            "MD: 叙述断片を丸ごと渡す → Edge 型なし → 推測しやすい",
            "グラフ: 型付き fact だけ渡す → 根拠が辿れる",
            "看板: Q5 でグラフ1つ vs 層分離の差も LLM 回答で見える",
        ],
    )


if __name__ == "__main__":
    main()
