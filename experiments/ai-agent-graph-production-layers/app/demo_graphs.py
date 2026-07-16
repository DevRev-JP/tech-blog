#!/usr/bin/env python3
"""graphs: 第1部5種 + 第2部 Edge 型の一覧."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent_langgraph import run_agent_once, run_dag_once, state_transitions  # noqa: E402
from app.answer_paths import CHANNEL_IDS  # noqa: E402
from app.graphs.dag_graph import dag_edges  # noqa: E402
from app.layers.audit_graph import performed_actions  # noqa: E402
from app.layers.context_graph import q8_context_nodes  # noqa: E402
from app.layers.graph import q1_customer  # noqa: E402
from app.layers.identity_graph import q6_same_customer  # noqa: E402
from app.layers.task_graph import task_prerequisites  # noqa: E402
from app.layers.temporal_graph import q7_escalated_at  # noqa: E402
from app.layers.workflow_graph import workflow_transitions  # noqa: E402
from app.shared import confirm_block  # noqa: E402


def main() -> None:
    print("[1] KG       : AFFECTS / OWNED_BY")
    print("    sample  ", q1_customer())

    print("[2] タスク   : TASK_PREREQUISITE")
    for a, b in task_prerequisites():
        print(f"    {a} -> {b}")

    print("[3] DAG      : LangGraph 固定エッジ（非巡回）")
    for src, dst in dag_edges():
        print(f"    {src} -> {dst}")
    print("    run     ", run_dag_once().get("log"))

    print("[4] WF       : WF_TRANSITION (approve/reject)")
    for t in workflow_transitions():
        print(f"    {t['from_step']} --{t['action']}--> {t['to_step']}")

    agent = run_agent_once()
    print("[5] ステート : state.phase")
    print(f"    phase={agent['phase']} wf_step={agent['wf_step']}")
    for src, dst in state_transitions():
        print(f"    {src} -> {dst}")

    print("\n--- 第2部 6特殊化（Edge 型） ---")
    print("[権限]     CAN_READ — graph.q4_can_read を stage2 で確認")
    print("[同一性]   SAME_AS ", q6_same_customer(CHANNEL_IDS))
    print("[時間軸]   Event BEFORE escalated_at=", q7_escalated_at())
    print("[監査]     PERFORMED", performed_actions())
    print("[コンテキスト] SCOPE_INCLUDES", q8_context_nodes())

    confirm_block(
        "第1部 5種類",
        [
            "[1] KG       : AFFECTS / OWNED_BY",
            "[2] タスク   : TASK_PREREQUISITE",
            "[3] DAG      : LangGraph 固定エッジ（非巡回）",
            "[4] WF       : WF_TRANSITION (approve/reject)",
            "[5] ステート : state.phase",
        ],
    )
    confirm_block(
        "第2部 6特殊化（stage2）",
        [
            "[権限]     Q3  CAN_READ",
            "[同一性]   Q2  SAME_AS",
            "[依存]     Q4  BLOCKS",
            "[時間軸]   Q7  Event BEFORE",
            "[監査]     Q6  audit_log + PERFORMED",
            "[コンテキスト] Q8 部分グラフ node_ids",
        ],
    )


if __name__ == "__main__":
    main()
