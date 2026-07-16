#!/usr/bin/env python3
"""ファイル vs グラフ、Neo4j単体 vs 分離 — 同じ問いの精度を並べて比較."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.answer_paths import (  # noqa: E402
    QUESTIONS,
    answer_file,
    answer_neo4j_only,
    answer_routed,
    precision_label,
)
from app.shared import confirm_block, narrate  # noqa: E402

COMPARE_IDS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]


def _print_row(label: str, result) -> None:
    print(f"  {label:<14} {precision_label(result.precision):<8} {result.reason}")
    print(f"  {'':14} → {result.value}")


def main() -> None:
    print("=" * 60)
    print("  前提: AI エージェントに何を読ませるか")
    print("  MD断片（叙述） vs グラフ（型付き Edge の fact）")
    print("  → ./run_demo.sh agent で LangGraph + Ollama の差を見る")
    print("=" * 60)
    narrate(
        [
            "同じ問いに対して「渡せる情報の確かさ」を表にします。AI は使いません。",
            "前半はファイルと層分離の比べ、後半は Neo4j だけと層分離の比べです。",
            "後半で差が出やすいのは、類似障害と件数集計の問いです。",
        ]
    )

    file_ans = {qid: answer_file(qid) for qid in COMPARE_IDS}
    neo_ans = {qid: answer_neo4j_only(qid) for qid in COMPARE_IDS}
    routed_ans = {qid: answer_routed(qid) for qid in COMPARE_IDS}

    print("\n" + "=" * 60)
    print("  A. MD断片 vs グラフ（AI に渡す情報の精度）")
    print("=" * 60)
    narrate(
        [
            "ファイル（叙述）と、層を分けたグラフを並べます。",
            "ファイル側は推測や不可が多く、グラフ側は確定に寄るのが成功の目安です。",
        ]
    )

    for qid in COMPARE_IDS:
        print(f"\n{qid}: {QUESTIONS[qid]}")
        _print_row("ファイル", file_ans[qid])
        _print_row("グラフ(分離)", routed_ans[qid])

    print("\n" + "=" * 60)
    print("  B. グラフ1つ(Neo4j) vs 分離")
    print("     全部 Graph DB に入れたときの精度落ち")
    print("=" * 60)
    narrate(
        [
            "全部を Neo4j に入れた場合と、層を分けた場合で差が出る問いだけ出します。",
            "類似障害と件数集計に注目してください。時間軸の問いは両方うまくいく例です。",
        ]
    )

    for qid in COMPARE_IDS:
        neo = neo_ans[qid]
        routed = routed_ans[qid]
        if neo.precision == routed.precision and neo.value == routed.value:
            continue
        print(f"\n{qid}: {QUESTIONS[qid]}")
        _print_row("Neo4j単体", neo)
        _print_row("分離", routed)
        if qid == "Q6":
            print("  ※ Issue.severity 集計(1件) vs audit_log 集計(複数件) の差が典型")

    print("\n" + "=" * 60)
    print("  C. まとめ")
    print("=" * 60)
    print("  1. ファイルは叙述は書けるが Edge の型がない → 推測・漏れ・集計不可")
    print("  2. グラフ(Neo4j)は関係をたどる問いでは高精度")
    print("  3. 全部 Neo4j だけだと類似検索と監査集計が弱い / ずれる")
    print("  4. 分離すると問いごとに最適層を叩き、同じ問いで精度が上がる")

    confirm_block(
        "compare",
        [
            "MD断片 vs グラフ: 顧客・同一性・権限・時間軸などで精度差を目視できる",
            "Neo4j単体 vs 分離: 類似障害と件数集計で渡す fact が変わる",
            "LangGraph 本体験: ./run_demo.sh agent",
        ],
    )


if __name__ == "__main__":
    main()
