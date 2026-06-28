"""Part2: Graphiti インデックス初期化（初回1回）."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared import create_graphiti_client, demo_run_context, is_demo_batch, milestone, section, step_print


async def main() -> None:
    with demo_run_context():
        if not is_demo_batch():
            step_print(1, 1, "Graphiti の indices/constraints を作成しています…")
        graphiti = create_graphiti_client()
        try:
            await graphiti.build_indices_and_constraints()
            if is_demo_batch():
                milestone("Graphiti 初期化")
            else:
                section("完了")
                print("Graphiti の初期化が完了しました。次: python app/demo_temporal.py ingest")
        finally:
            await graphiti.close()


if __name__ == "__main__":
    asyncio.run(main())
