#!/usr/bin/env python3
"""段階0: fragments.json 直渡し（推論的・ファイルの限界）."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.answer_paths import QUESTIONS, answer_file, precision_label  # noqa: E402
from app.shared import confirm_block  # noqa: E402

FOCUS = ["Q1", "Q5", "Q6", "Q7"]


def main() -> None:
    print("段階0 — ファイル断片（fragments.json）のみ")
    print("Edge の型がない＝顧客・同一性・時系列・集計を機械が保証できない\n")

    for qid in FOCUS:
        r = answer_file(qid)
        print(f"{qid}: {QUESTIONS[qid]}")
        print(f"  精度: {precision_label(r.precision)}")
        print(f"  回答: {r.value}")
        print(f"  理由: {r.reason}\n")

    confirm_block(
        "stage0",
        [
            "Q1: 断片ごとに顧客の明示度が違う（推測になりやすい）",
            "Q5: 集計不可（叙述の「気がする」だけ）",
            "Q6: SAME_AS なし → 別チャネル＝別顧客と誤認",
            "Q7: 時系列 Edge なし → 30分前を辿れない",
            "→ ./run_demo.sh compare でグラフとの差を並べて見る",
        ],
    )


if __name__ == "__main__":
    main()
