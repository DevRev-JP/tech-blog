#!/usr/bin/env python3
"""setup: Neo4j seed + Qdrant + SQLite."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.layers.vector import seed_collection, using_semantic_embedding  # noqa: E402
from app.shared import DATA_DIR, confirm_block, init_audit_db, run_cypher_file  # noqa: E402


def main() -> None:
    print("Loading Neo4j seed...")
    run_cypher_file(DATA_DIR / "incident.cypher")
    print("Initializing SQLite audit.db...")
    init_audit_db()
    semantic = using_semantic_embedding()
    n = seed_collection()
    embed_note = (
        "Ollama 埋め込み（意味的類似）"
        if semantic
        else "疑似ベクトル（フォールバック・意味を反映しない）"
    )
    print(f"Seeded Qdrant collection ({n} docs, {embed_note}).")
    if not semantic:
        print("  ⚠ 類似障害（Q5）の意味的類似を体験するには Ollama を起動してください:")
        print("    ollama serve && ollama pull nomic-embed-text → 再度 setup")
    confirm_block(
        "setup",
        [
            "Neo4j: incident.cypher 適用済み",
            f"Qdrant: {n} 件 upsert（{embed_note}）",
            "SQLite: audit.db 初期化済み",
        ],
    )


if __name__ == "__main__":
    main()
