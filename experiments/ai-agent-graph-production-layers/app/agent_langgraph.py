"""LangGraph エージェント — DAG + WF + ステート."""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.graphs.dag_graph import build_dag_graph
from app.shared import ISSUE_ID


class AgentState(TypedDict):
    phase: Literal["investigating", "waiting_approval", "done"]
    wf_step: str
    message: str


def _investigate(state: AgentState) -> AgentState:
    return {
        "phase": "investigating",
        "wf_step": "wf-investigating",
        "message": state.get("message", "") + " [investigate]",
    }


def _wait_approval(state: AgentState) -> AgentState:
    return {
        "phase": "waiting_approval",
        "wf_step": "wf-review",
        "message": state.get("message", "") + " [wait_approval]",
    }


def _complete(state: AgentState) -> AgentState:
    return {
        "phase": "done",
        "wf_step": "wf-done",
        "message": state.get("message", "") + " [done]",
    }


def build_agent_graph():
    g = StateGraph(AgentState)
    g.add_node("investigate", _investigate)
    g.add_node("wait_approval", _wait_approval)
    g.add_node("complete", _complete)
    g.add_edge(START, "investigate")
    g.add_edge("investigate", "wait_approval")
    g.add_edge("wait_approval", "complete")
    g.add_edge("complete", END)
    return g.compile()


def state_transitions() -> list[tuple[str, str]]:
    return [
        ("investigating", "waiting_approval"),
        ("waiting_approval", "done"),
    ]


def run_agent_once() -> AgentState:
    graph = build_agent_graph()
    return graph.invoke({"phase": "investigating", "wf_step": "wf-investigating", "message": ISSUE_ID})


def run_dag_once() -> dict:
    return build_dag_graph().invoke({"step": "", "log": []})
