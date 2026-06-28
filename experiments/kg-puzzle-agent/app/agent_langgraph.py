"""Part1: LangGraph — retrieve_graph_context → generate."""

from __future__ import annotations

import argparse
import operator
import sys
from pathlib import Path
from typing import Annotated, Sequence, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graph_retriever import GraphRetriever
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph

from shared import get_llm, get_neo4j_driver, section, step_print


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    graph_context: str
    user_id: str


def retrieve_graph_context(state: AgentState) -> dict:
    last = state["messages"][-1].content
    user_id = state.get("user_id", "user_tanaka")
    driver = get_neo4j_driver()
    retriever = GraphRetriever(driver)
    context = retriever.get_context_with_permissions(str(last), user_id=user_id)
    driver.close()
    return {"graph_context": context}


def generate_response(state: AgentState) -> dict:
    llm = get_llm()
    graph_context = state.get("graph_context", "")
    messages = state["messages"]
    system = f"""あなたは質問応答エージェントです。
以下のナレッジグラフコンテキストだけを根拠に回答してください。

## ナレッジグラフ コンテキスト
{graph_context}
"""
    prompt_messages = [{"role": "system", "content": system}]
    for m in messages:
        role = "user" if m.type == "human" else "assistant"
        prompt_messages.append({"role": role, "content": m.content})
    response = llm.invoke(
        "\n".join(f"{p['role']}: {p['content']}" for p in prompt_messages)
    )
    return {"messages": [AIMessage(content=response.content)]}


def build_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve_context", retrieve_graph_context)
    workflow.add_node("generate", generate_response)
    workflow.set_entry_point("retrieve_context")
    workflow.add_edge("retrieve_context", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--question",
        default="プロジェクトAlphaの担当チームと技術スタックは？",
    )
    parser.add_argument("--user-id", default="user_tanaka")
    args = parser.parse_args()

    step_print(1, 1, "LangGraph エージェントを実行しています…")
    agent = build_agent()
    result = agent.invoke(
        {
            "messages": [HumanMessage(content=args.question)],
            "user_id": args.user_id,
            "graph_context": "",
        }
    )

    section("参照したグラフ")
    print(result.get("graph_context", ""))
    section("回答")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
