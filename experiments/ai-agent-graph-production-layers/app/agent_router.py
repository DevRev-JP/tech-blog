"""LangGraph エージェント — コンテキスト取得 → Ollama 回答.

第3部の核心: AI が MD 断片を読むか、グラフ（層分離）を読むかで答えが変わる。
"""

from __future__ import annotations

import operator
from functools import lru_cache
from typing import Annotated, Literal, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from app.answer_paths import QUESTION_META
from app.context_builders import build_context
from app.shared import get_llm, ollama_available

Mode = Literal["file", "neo4j_only", "routed"]


class AgentState(TypedDict):
    mode: Mode
    question_id: str
    question: str
    context: str
    context_kind: str
    layer_route: str
    graph_kind: str
    messages: Annotated[Sequence[BaseMessage], operator.add]


def retrieve_context(state: AgentState) -> dict:
    mode = state["mode"]
    qid = state["question_id"]
    ctx, kind, route = build_context(mode, qid)
    return {
        "context": ctx,
        "context_kind": kind,
        "layer_route": route,
    }


def route_layer(state: AgentState) -> dict:
    """問いをどの物理層 / どの種のグラフに割り当てたかを決める（段階0は層分離なし）."""
    qid = state["question_id"]
    meta = QUESTION_META.get(qid)
    kind = meta.graph_kind if meta else "?"
    if state["mode"] == "file":
        route = "層ルーティングなし（段階0: 全断片をそのまま渡す）"
    else:
        route = state.get("layer_route") or "（物理層未特定）"
    return {"graph_kind": kind, "layer_route": route}


def generate(state: AgentState) -> dict:
    if not ollama_available():
        skip = "[Ollama 未起動] 上記コンテキストの差だけ確認してください。"
        return {"messages": [AIMessage(content=skip)]}

    llm = get_llm()
    system = f"""あなたは障害対応アシスタントです。
以下のコンテキスト**だけ**を根拠に、簡潔に日本語で答えてください。
根拠が不足している場合は「断定できない」と述べ、推測で補完しないでください。

## コンテキスト種別
{state.get('context_kind')} / 効くグラフ: {state.get('graph_kind')} / 取得経路: {state.get('layer_route')}

## コンテキスト
{state.get('context', '')}
"""
    question = state["question"]
    response = llm.invoke(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
    )
    return {"messages": [AIMessage(content=response.content)]}


@lru_cache(maxsize=1)
def build_agent():
    """グラフ構造は不変なので1度だけコンパイルして使い回す."""
    g = StateGraph(AgentState)
    g.add_node("retrieve_context", retrieve_context)
    g.add_node("route_layer", route_layer)
    g.add_node("generate", generate)
    g.add_edge(START, "retrieve_context")
    g.add_edge("retrieve_context", "route_layer")
    g.add_edge("route_layer", "generate")
    g.add_edge("generate", END)
    return g.compile()


def run_agent(mode: Mode, question_id: str, question: str) -> AgentState:
    agent = build_agent()
    return agent.invoke(
        {
            "mode": mode,
            "question_id": question_id,
            "question": question,
            "context": "",
            "context_kind": "",
            "layer_route": "",
            "graph_kind": "",
            "messages": [HumanMessage(content=question)],
        }
    )
