#!/usr/bin/env python3
"""段階2: Q1〜Q8 ルーティング（物理層分離）."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.answer_paths import QUESTIONS, answer_routed, precision_label  # noqa: E402
from app.shared import confirm_block  # noqa: E402


def main() -> None:
    print("段階2 — LangGraph エージェントが層分離したグラフを読む\n")
    print("（retrieve_context → route_layer → generate。詳細は ./run_demo.sh agent）\n")
    for qid in QUESTIONS:
        r = answer_routed(qid)
        # 物理層は answer_routed().reason に集約（stage2 独自の層マップは持たない）
        print(f"{qid} [{r.reason}] {precision_label(r.precision)}")
        print(f"  {QUESTIONS[qid]}")
        print(f"  → {r.value}\n")

    confirm_block(
        "stage2",
        [
            "Q1〜Q8 がそれぞれ最適な物理層で答えられる",
            "ファイル/Neo4j単体との差は compare で確認",
            "./run_demo.sh full = scenario + agent + compare",
        ],
    )


if __name__ == "__main__":
    main()
