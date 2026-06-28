"""Part1: 同一質問 × ユーザーでグラフコンテキストの差分を表示."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graph_retriever import GraphRetriever
from shared import DATA_DIR, get_neo4j_driver, section, step_print


def main() -> None:
    data = json.loads((DATA_DIR / "tool_fragments.json").read_text(encoding="utf-8"))
    question = data["question"]

    step_print(1, 1, "権限の違いでグラフコンテキストがどう変わるか確認します…")
    driver = get_neo4j_driver()
    retriever = GraphRetriever(driver)

    tanaka_ctx = retriever.get_context_with_permissions(question, user_id="user_tanaka")
    guest_ctx = retriever.get_context_with_permissions(question, user_id="user_guest")
    driver.close()

    section("user_tanaka（Team A メンバー — Alpha にアクセス可）")
    print(tanaka_ctx)

    section("user_guest（Alpha へのアクセス権なし）")
    print(guest_ctx)

    section("ポイント")
    print(
        "Skill プロンプトで「見るな」と書いても LLM に全文渡せば漏れます。"
        "グラフのパストラバーサル時点で到達不能なノードはコンテキストに含まれません。"
    )


if __name__ == "__main__":
    main()
