"""[3部] LangGraph DAG — 第1部 [3] 実行順序グラフ."""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class DagState(TypedDict):
    step: str
    log: list[str]


def _fetch_context(state: DagState) -> DagState:
    log = list(state.get("log", []))
    log.append("fetch_context")
    return {"step": "fetch_context", "log": log}


def _route_layer(state: DagState) -> DagState:
    log = list(state.get("log", []))
    log.append("route_layer")
    return {"step": "route_layer", "log": log}


def _generate(state: DagState) -> DagState:
    log = list(state.get("log", []))
    log.append("generate")
    return {"step": "generate", "log": log}


def build_dag_graph():
    g = StateGraph(DagState)
    g.add_node("fetch_context", _fetch_context)
    g.add_node("route_layer", _route_layer)
    g.add_node("generate", _generate)
    g.add_edge(START, "fetch_context")
    g.add_edge("fetch_context", "route_layer")
    g.add_edge("route_layer", "generate")
    g.add_edge("generate", END)
    return g.compile()


def dag_edges() -> list[tuple[str, str]]:
    return [
        ("START", "fetch_context"),
        ("fetch_context", "route_layer"),
        ("route_layer", "generate"),
        ("generate", "END"),
    ]
