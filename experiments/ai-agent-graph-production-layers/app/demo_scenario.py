#!/usr/bin/env python3
"""scenario: 障害 INC-001 を第1部の5種類のグラフで1本の物語として辿る.

S1 顧客特定       → [1] ナレッジグラフ
S2 次にやること   → [2] タスクグラフ
S3 診断の実行順   → [3] 実行順序グラフ（DAG）
S4 エスカレーション → [4] ワークフローグラフ
S5 今どの段階か   → [5] ステートグラフ

各ステップで「このグラフがないと何が起きるか」を並べ、種類ごとに役割が違うと分かるようにする。
LLM 不要（Neo4j seed のみ）。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.agent_langgraph import run_agent_once, run_dag_once, state_transitions  # noqa: E402
from app.graphs.dag_graph import dag_edges  # noqa: E402
from app.layers.graph import q1_customer  # noqa: E402
from app.layers.task_graph import task_prerequisites  # noqa: E402
from app.layers.workflow_graph import workflow_transitions  # noqa: E402
from app.shared import confirm_block, narrate  # noqa: E402


def _header(step: str, part_kind: str, question: str) -> None:
    print("\n" + "=" * 62)
    print(f"  {step}  —  {part_kind}")
    print(f"  問い: {question}")
    print("=" * 62)


def s1_customer() -> None:
    _header("S1 顧客特定", "[1] ナレッジグラフ", "INC-001 の顧客は？")
    narrate(
        [
            "チケットから「どの製品か」「どの顧客か」を Neo4j で辿ります。",
            "下に「顧客=Globex Corp」と出れば成功です。",
        ]
    )
    v = q1_customer()
    print("  グラフ: (Issue)-[:AFFECTS]->(Product)-[:OWNED_BY]->(Customer)")
    print(f"    → 製品={v.get('product')} / 顧客={v.get('customer')}")
    print("  無いと困ること: Jira・Slack・メールの記述が食い違っても、どれが正しいか決められない")


def s2_tasks() -> None:
    _header("S2 次にやること", "[2] タスクグラフ", "調査の前提タスクは？")
    narrate(
        [
            "調査の前に「何を済ませておく必要があるか」を Neo4j から読みます。",
            "下にタスクが「─必要→」でつながっていれば成功です。",
        ]
    )
    print("  グラフ: (IncidentTask)-[:TASK_PREREQUISITE]->(IncidentTask)")
    for a, b in task_prerequisites():
        print(f"    {a} ─必要→ {b}")
    print("  無いと困ること: メモの箇条書きだけだと、前提の前後関係を毎回推測することになる")


def s3_dag() -> None:
    _header("S3 診断の実行順", "[3] 実行順序グラフ（DAG）", "取得パイプラインをどの順で回すか？")
    narrate(
        [
            "エージェントが情報を取る順番を、LangGraph の矢印として定義し、一度動かします。",
            "下の「実行結果」に fetch_context → route_layer → generate と並んでいれば成功です。",
        ]
    )
    print("  定義した順番:")
    for src, dst in dag_edges():
        print(f"    {src} -> {dst}")
    result = run_dag_once()
    print(f"  実行結果: {' → '.join(result.get('log') or [])}")
    print("  無いと困ること: 順番が if/else の中に隠れ、誰も処理順を説明しづらい")


def s4_workflow() -> None:
    _header("S4 エスカレーション", "[4] ワークフローグラフ", "P0 承認・差し戻しのフローは？")
    narrate(
        [
            "人の承認や差し戻しがある流れを Neo4j から読みます（戻れるので、S3 の一方通行とは違います）。",
            "下に approve / reject / submit の矢印が出ていれば成功です。",
        ]
    )
    print("  グラフ: (WfStep)-[:WF_TRANSITION {action}]->(WfStep)")
    for t in workflow_transitions():
        print(f"    {t['from_step']} --{t['action']}--> {t['to_step']}")
    print("  無いと困ること: 差し戻しで前の工程に戻る、という流れを型として持てない")


def s5_state() -> None:
    _header("S5 今どの段階か", "[5] ステートグラフ", "エージェントは今どのフェーズ？")
    narrate(
        [
            "エージェントが「いま調査中か／承認待ちか／完了か」を LangGraph の状態として持ち、動かした結果を見ます。",
            "下に phase=done のように現在地が出ていれば成功です。",
        ]
    )
    agent = run_agent_once()
    print("  実行後の状態:")
    print(f"    phase={agent['phase']} / wf_step={agent['wf_step']}")
    print("  取りうる遷移:")
    for src, dst in state_transitions():
        print(f"    {src} -> {dst}")
    print("  無いと困ること: 「今どこにいるか」がプロンプト頼みになり、会話のたびにブレる")


def main() -> None:
    print("障害 INC-001（Acme Search / Globex Corp）")
    print("同じ障害を、5つの場面で別々のグラフに当てはめて見ます。")
    narrate(
        [
            "S1〜S5 を上から順に見てください。",
            "各ステップは「何をするか」→「成功の目安」→「実際の結果」の順です。",
            "くわしい背景は記事側です。ここでは結果が目安どおりかを確認します。",
        ]
    )
    s1_customer()
    s2_tasks()
    s3_dag()
    s4_workflow()
    s5_state()

    confirm_block(
        "scenario",
        [
            "S1: Neo4j で顧客名が取れた",
            "S2: Neo4j でタスクの前提関係が取れた",
            "S3: LangGraph の実行ログが fetch_context → route_layer → generate",
            "S4: Neo4j で承認・差し戻しの矢印が見えた",
            "S5: LangGraph 実行後に phase など現在地が出た",
            "→ 同じ障害でも、場面ごとに使うグラフが違う",
        ],
    )


if __name__ == "__main__":
    main()
