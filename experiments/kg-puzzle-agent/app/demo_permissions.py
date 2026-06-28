"""Part1: 権限 — グラフ遮断 vs Skill 全文漏洩."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_skills_only import run_mode_a, run_mode_b
from graph_retriever import GraphRetriever
from shared import DATA_DIR, checkpoint, demo_run_context, get_neo4j_driver, section, step_print


def main() -> None:
    with demo_run_context():
        _run_permissions_demo()


def _run_permissions_demo() -> None:
    data = json.loads((DATA_DIR / "tool_fragments.json").read_text(encoding="utf-8"))
    question = data["question"]

    step_print(1, 3, "同一質問 × ユーザーでグラフコンテキストの差分…")
    driver = get_neo4j_driver()
    retriever = GraphRetriever(driver)
    tanaka_ctx = retriever.get_context_with_permissions(question, user_id="user_tanaka")
    guest_ctx = retriever.get_context_with_permissions(question, user_id="user_guest")
    driver.close()

    section("user_tanaka（Team A — Alpha にアクセス可）")
    print(tanaka_ctx)

    section("user_guest（Alpha へのアクセス権なし）")
    print(guest_ctx)

    leak = data["leak_demo"]
    step_print(2, 3, "秘匿予算 — 断片直渡しはプロンプト禁止でも漏れうる…")
    section(f"断片直渡し（Skill 相当）+ 禁止指示 → 質問: {leak['question']}")
    leaked = run_mode_a(
        leak["question"],
        leak["fragments"],
        system_preamble=leak["guest_instruction"],
    )
    print(leaked)
    if "800" in leaked:
        print("\n→ プロンプトで「社外秘を答えるな」と書いても、断片に全文があれば LLM が漏らしうる。")
    else:
        print("\n→ 今回のモデルでは抑制されたが、断片を渡す限り漏洩リスクは残る。")

    step_print(3, 3, "同一質問 × user_guest — グラフは到達前に遮断…")
    section("グラフ（user_guest）")
    context, answer_b = run_mode_b(leak["question"], user_id="user_guest")
    print("## 参照したグラフ")
    print(context)
    print()
    print("## 回答")
    print(answer_b)

    section("ポイント")
    print(
        "権限はプロンプトではなく取得段階で効かせる。"
        "断片直渡し（Skill 相当）は断片を LLM に渡した時点で秘匿の境界が崩れうる。"
        "グラフのパストラバーサルでは到達不能なノードはコンテキストに含まれない。"
    )
    checkpoint(
        "Part1 権限",
        [
            "user_guest のグラフに Deal / 800万 が含まれない",
            "断片直渡し + 禁止指示でも 800万 が返る（漏洩デモ）",
            "グラフ guest は「情報が見つかりませんでした」",
        ],
    )


if __name__ == "__main__":
    main()
