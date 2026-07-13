#!/usr/bin/env python3
"""scenario: 障害 INC-001 を第1部5種の順に1本の物語で辿る（G2）.

S1 顧客特定       → [1] ナレッジグラフ
S2 次にやること   → [2] タスクグラフ
S3 診断の実行順   → [3] 実行順序グラフ（DAG）
S4 エスカレーション → [4] ワークフローグラフ
S5 今どの段階か   → [5] ステートグラフ

各ステップで「この種がないと何が曖昧になるか」を並べ、5種が別役割だと体感する。
LLM 不要（Neo4j seed のみ）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent_langgraph import run_agent_once, state_transitions  # noqa: E402
from app.graphs.dag_graph import dag_edges  # noqa: E402
from app.layers.graph import q1_customer  # noqa: E402
from app.layers.task_graph import task_prerequisites  # noqa: E402
from app.layers.workflow_graph import workflow_transitions  # noqa: E402
from app.shared import confirm_block  # noqa: E402


def _header(step: str, part_kind: str, question: str) -> None:
    print("\n" + "=" * 62)
    print(f"  {step}  —  {part_kind}")
    print(f"  問い: {question}")
    print("=" * 62)


def s1_customer() -> None:
    _header("S1 顧客特定", "[1] ナレッジグラフ", "INC-001 の顧客は？")
    v = q1_customer()
    print("  グラフ: (Issue)-[:AFFECTS]->(Product)-[:OWNED_BY]->(Customer)")
    print(f"    → 製品={v.get('product')} / 顧客={v.get('customer')}")
    print("  この種がないと: MD 断片のどれ（Jira/Slack/メール）を信じるか曖昧")


def s2_tasks() -> None:
    _header("S2 次にやること", "[2] タスクグラフ", "調査の前提タスクは？")
    print("  グラフ: (IncidentTask)-[:TASK_PREREQUISITE]->(IncidentTask)")
    for a, b in task_prerequisites():
        print(f"    {a} ─必要→ {b}")
    print("  この種がないと: MD の箇条書きから前提関係を毎回推測する")


def s3_dag() -> None:
    _header("S3 診断の実行順", "[3] 実行順序グラフ（DAG）", "取得パイプラインをどの順で回すか？")
    print("  グラフ: LangGraph 固定有向エッジ（非巡回）")
    for src, dst in dag_edges():
        print(f"    {src} -> {dst}")
    print("  この種がないと: if/else に埋もれて実行順序が読めない")


def s4_workflow() -> None:
    _header("S4 エスカレーション", "[4] ワークフローグラフ", "P0 承認・差し戻しのフローは？")
    print("  グラフ: (WfStep)-[:WF_TRANSITION {action}]->(WfStep)（循環あり）")
    for t in workflow_transitions():
        print(f"    {t['from_step']} --{t['action']}--> {t['to_step']}")
    print("  この種がないと: 差し戻しの循環を型として持てない")


def s5_state() -> None:
    _header("S5 今どの段階か", "[5] ステートグラフ", "エージェントは今どのフェーズ？")
    agent = run_agent_once()
    print("  グラフ: LangGraph AgentState.phase（ランタイムの現在状態）")
    print(f"    現在 phase={agent['phase']} / wf_step={agent['wf_step']}")
    for src, dst in state_transitions():
        print(f"    {src} -> {dst}")
    print("  この種がないと: 今の状態がプロンプト依存でブレる")


def main() -> None:
    print("障害 INC-001（Acme Search / Globex Corp）を5種のグラフで辿る")
    print("同じ1件の障害でも、問いが変わると効くグラフの種類が変わる。")
    s1_customer()
    s2_tasks()
    s3_dag()
    s4_workflow()
    s5_state()

    confirm_block(
        "scenario",
        [
            "S1 [1]KG    : 顧客特定は AFFECTS / OWNED_BY の traversal",
            "S2 [2]タスク: 前提は TASK_PREREQUISITE（実行順序ではない）",
            "S3 [3]DAG   : 実行順は LangGraph 固定エッジ（非巡回）",
            "S4 [4]WF    : 承認・差し戻しは WF_TRANSITION（循環あり）",
            "S5 [5]ステート: 現在フェーズは AgentState.phase",
            "→ 5種は同じ障害の中で別の問い・別の制御に効いている",
        ],
    )


if __name__ == "__main__":
    main()
