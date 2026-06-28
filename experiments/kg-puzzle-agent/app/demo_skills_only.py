"""Part0: Skill 断片のみ vs コンテキストグラフの A/B 比較."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graph_retriever import GraphRetriever
from shared import DATA_DIR, get_llm, get_neo4j_driver, section


def load_fragments() -> dict:
    return json.loads((DATA_DIR / "tool_fragments.json").read_text(encoding="utf-8"))


def run_mode_a(question: str, fragments: list[dict]) -> str:
    llm = get_llm()
    fragment_text = "\n\n".join(
        f"[{f['label']} / source={f['source']}]\n{f['text']}" for f in fragments
    )
    prompt = f"""あなたは Skill/MCP で複数ソースから取得した断片だけを頼りに回答するエージェントです。
断片間の関係は明示されていません。断片の内容だけから推測して回答してください。

## Skill で取得した断片
{fragment_text}

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


def main() -> None:
    data = load_fragments()
    question = data["question"]
    fragments = data["fragments"]

    section("A: Skill/MCP 断片のみ（同一事実・接続情報なし）")
    print("質問:", question)
    print()
    answer_a = run_mode_a(question, fragments)
    print(answer_a)

    section("B: コンテキストグラフ（同一事実・関係が固定）")
    context, answer_b = run_mode_b(question)
    print("## 参照したグラフ")
    print(context)
    print()
    print("## 回答")
    print(answer_b)

    section("サマリ")
    print(
        "同じ事実を、Skill 断片だけ渡すと LLM がつなぎ方を推測します。"
        "コンテキストグラフなら関係が固定されているので、答えと根拠が安定します。"
    )


if __name__ == "__main__":
    main()
