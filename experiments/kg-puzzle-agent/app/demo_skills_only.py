"""Part0: Skill 断片のみ vs コンテキストグラフの A/B 比較."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graph_retriever import GraphRetriever
from shared import DATA_DIR, checkpoint, demo_run_context, get_llm, get_neo4j_driver, is_demo_batch, section


def load_fragments() -> dict:
    return json.loads((DATA_DIR / "tool_fragments.json").read_text(encoding="utf-8"))


def _fragment_block(fragments: list[dict]) -> str:
    return "\n\n".join(
        f"[{f['label']} / source={f['source']}]\n{f['text']}" for f in fragments
    )


def run_mode_a(
    question: str,
    fragments: list[dict],
    *,
    system_preamble: str = "",
) -> str:
    llm = get_llm()
    preamble = system_preamble or (
        "あなたは Skill/MCP で複数ソースから取得した断片だけを頼りに回答するエージェントです。\n"
        "断片間の関係は明示されていません。断片の内容だけから推測して回答してください。"
    )
    prompt = f"""{preamble}

## Skill で取得した断片
{_fragment_block(fragments)}

## 質問
{question}

## 回答（日本語、簡潔に）
"""
    return llm.invoke(prompt).content


def run_mode_b(question: str, user_id: str = "user_tanaka") -> tuple[str, str]:
    driver = get_neo4j_driver()
    retriever = GraphRetriever(driver)
    context = retriever.get_context_with_permissions(question, user_id=user_id)
    driver.close()

    llm = get_llm()
    prompt = f"""あなたは質問応答エージェントです。
以下のナレッジグラフから取得した構造化コンテキストだけを根拠に回答してください。
コンテキストにないことは推測せず「情報が見つかりませんでした」と答えてください。

## 参照したグラフ
{context}

## 質問
{question}

## 回答（日本語、簡潔に。根拠はグラフの関係に沿うこと）
"""
    return context, llm.invoke(prompt).content


def _run_baseline_compare(data: dict) -> None:
    question = data["question"]
    fragments = data["fragments"]

    section("Q1: 同一事実 — Skill 断片 vs グラフ")
    print("質問:", question)
    print()

    section("A: Skill/MCP 断片のみ（接続情報なし）")
    answer_a = run_mode_a(question, fragments)
    print(answer_a)

    section("B: コンテキストグラフ（関係が固定）")
    context, answer_b = run_mode_b(question)
    print("## 参照したグラフ")
    print(context)
    print()
    print("## 回答")
    print(answer_b)


def _run_trap_compare(data: dict) -> None:
    trap = data["trap_question"]
    question = trap["question"]

    section("Q2: 矛盾断片 — Skill だと推測が外れやすい")
    print("質問:", question)
    print("グラフの正:", trap["graph_truth"])
    print()

    section("A: 矛盾する断片だけ（Team B vs Team A）")
    answer_a = run_mode_a(question, trap["fragments"])
    print(answer_a)
    if "Team B" in answer_a or "チームB" in answer_a or "team b" in answer_a.lower():
        print("\n→ 断片の古い情報（Team B）を採用。グラフの OWNED_BY Team A と不一致。")
    else:
        print("\n→ モデルによっては正答することもあるが、断片だけでは根拠が不安定。")

    section("B: グラフ（OWNED_BY が固定）")
    context, answer_b = run_mode_b(question)
    print("## 参照したグラフ")
    print(context)
    print()
    print("## 回答")
    print(answer_b)


def main() -> None:
    with demo_run_context():
        data = load_fragments()
        if data.get("story") and not is_demo_batch():
            section("ストーリー")
            print(data["story"])

        _run_baseline_compare(data)
        _run_trap_compare(data)

        if not is_demo_batch():
            section("サマリ")
            print(
                "Q1: 同じ正答でも、B だけが関係付きの根拠（## 参照したグラフ）を示せる。\n"
                "Q2: 断片が矛盾すると Skill は推測依存。グラフは OWNED_BY で Team A に固定される。"
            )
        checkpoint(
            "Part0",
            [
                "Q1: B に `## 参照したグラフ` と OWNED_BY / USES が出ている",
                "Q2: A が Team B、B が Team A（グラフ固定 vs 断片推測）",
            ],
        )


if __name__ == "__main__":
    main()
