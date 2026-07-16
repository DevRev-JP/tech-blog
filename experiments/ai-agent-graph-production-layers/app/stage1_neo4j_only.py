#!/usr/bin/env python3
"""全部 Neo4j に押し込むつらさ（集計・類似は別層向き）."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.answer_paths import QUESTIONS, answer_neo4j_only, answer_routed, precision_label  # noqa: E402
from app.shared import confirm_block  # noqa: E402

FOCUS = ["Q5", "Q6", "Q1", "Q4"]


def main() -> None:
    print("単一 Graph DB（Neo4j）に全部載せた想定")
    print("関係 traversal は強いが、類似検索・監査集計は別層の方が精度が出る\n")

    for qid in FOCUS:
        neo = answer_neo4j_only(qid)
        routed = answer_routed(qid)
        print(f"{qid}: {QUESTIONS[qid]}")
        print(f"  Neo4j単体 {precision_label(neo.precision)} → {neo.value}")
        if neo.precision != routed.precision or neo.value != routed.value:
            print(f"  分離後   {precision_label(routed.precision)} → {routed.value}")
            print(f"  差分: {neo.reason}")
        else:
            print(f"  （分離後も同精度 — Graph DB 向きの問い）")
        print()

    confirm_block(
        "stage1",
        [
            "Q1/Q4: Neo4j 単体で十分（◎）",
            "Q5: キーワードだけ → Qdrant 分離で過去障害を拾える",
            "Q6: Issue.severity 集計 vs audit_log 集計で件数がずれる",
            "→ ./run_demo.sh compare で全問の精度差を一覧",
        ],
    )


if __name__ == "__main__":
    main()
