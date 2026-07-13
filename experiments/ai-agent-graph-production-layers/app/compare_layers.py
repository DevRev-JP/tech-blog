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
from app.shared import confirm_block  # noqa: E402

# 体感の差が最も出る問い（全8問は stage2 で）
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

    # 各問いの回答は DB クエリを伴うので、段階ごとに1度だけ計算して使い回す
    file_ans = {qid: answer_file(qid) for qid in COMPARE_IDS}
    neo_ans = {qid: answer_neo4j_only(qid) for qid in COMPARE_IDS}
    routed_ans = {qid: answer_routed(qid) for qid in COMPARE_IDS}

    print("\n" + "=" * 60)
    print("  A. MD断片 vs グラフ（AI に渡す情報の精度）")
    print("=" * 60)

    for qid in COMPARE_IDS:
        print(f"\n{qid}: {QUESTIONS[qid]}")
        _print_row("ファイル", file_ans[qid])
        _print_row("グラフ(分離)", routed_ans[qid])

    print("\n" + "=" * 60)
    print("  B. グラフ1つ(Neo4j) vs 分離（段階1 vs 段階2）")
    print("     全部 Graph DB に入れたときの精度落ち")
    print("=" * 60)

    for qid in COMPARE_IDS:
        neo = neo_ans[qid]
        routed = routed_ans[qid]
        if neo.precision == routed.precision and neo.value == routed.value:
            continue
        print(f"\n{qid}: {QUESTIONS[qid]}")
        _print_row("Neo4j単体", neo)
        _print_row("分離", routed)
        if qid == "Q5":
            print("  ※ Q5: Issue.severity 集計(1件) vs audit_log 集計(複数件) の差が典型")

    print("\n" + "=" * 60)
    print("  C. まとめ（言えること）")
    print("=" * 60)
    print("  1. ファイルは叙述は書けるが Edge の型がない → 推測・漏れ・集計不可")
    print("  2. グラフ(Neo4j)は関係 traversal は高精度（Q1/Q3/Q4/Q6）")
    print("  3. 全部 Neo4j だけだと類似検索(Q2)と監査集計(Q5)が弱い/ずれる")
    print("  4. 分離すると問いごとに最適層を叩き、同じ Q で精度が上がる")

    confirm_block(
        "compare",
        [
            "MD断片 vs グラフ: Q4/Q6/Q7 で精度差を目視できる",
            "Neo4j単体 vs 分離: Q2/Q5 で AI に渡す fact が変わる",
            "LangGraph 本体験: ./run_demo.sh agent",
            "記事の核心「AIが読むもの」の差を自分で説明できる",
        ],
    )


if __name__ == "__main__":
    main()
