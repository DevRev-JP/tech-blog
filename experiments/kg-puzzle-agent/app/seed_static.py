"""Part1 用: Project Alpha グラフを Cypher で投入."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared import DATA_DIR, demo_run_context, get_neo4j_driver, is_demo_batch, milestone, section, step_print


def main() -> None:
    with demo_run_context():
        _run_seed()


def _run_seed() -> None:
    if not is_demo_batch():
        step_print(1, 1, "Project Alpha グラフを Neo4j に投入しています…")
    cypher_path = DATA_DIR / "project_alpha.cypher"
    statements = [
        s.strip()
        for s in cypher_path.read_text(encoding="utf-8").split(";")
        if s.strip() and not s.strip().startswith("//")
    ]

    driver = get_neo4j_driver()
    with driver.session() as session:
        for stmt in statements:
            session.run(stmt)
    driver.close()

    if is_demo_batch():
        milestone("Project Alpha グラフ投入")
        return

    section("完了")
    print("Project Alpha グラフの投入が完了しました。")
    print("Neo4j Browser: http://localhost:7474 （neo4j / .env のパスワード）")
    print("  → README 付録 Neo4j（Part0/1 用 Cypher · Part2 実行後は 0 件になるので注意）")


if __name__ == "__main__":
    main()
