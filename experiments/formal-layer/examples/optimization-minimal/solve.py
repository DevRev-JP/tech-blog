"""
制約ソルバ（最適化レイヤ）の最小構成例

記事「LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド」の
ハンズオンセクション「OR-Tools の最小例」に対応する例です。

実行方法:
    pip install ortools
    python solve.py
"""

from ortools.sat.python import cp_model

model = cp_model.CpModel()
agents = ["A", "B"]
tasks = ["T1", "T2", "T3"]

x = {}
for i, a in enumerate(agents):
    for j, t in enumerate(tasks):
        x[(i, j)] = model.NewBoolVar(f"x_{a}_{t}")

# 各タスクは必ず1つのエージェントに割り当てられる
for j, _ in enumerate(tasks):
    model.Add(sum(x[(i, j)] for i, _ in enumerate(agents)) == 1)

# 各エージェントは最大2つのタスクを処理できる
for i, _ in enumerate(agents):
    model.Add(sum(x[(i, j)] for j, _ in enumerate(tasks)) <= 2)

solver = cp_model.CpSolver()
status = solver.Solve(model)

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print("✅ 解が見つかりました:")
    for i, a in enumerate(agents):
        for j, t in enumerate(tasks):
            if solver.Value(x[(i, j)]) == 1:
                print(f"  {a} -> {t}")
else:
    print("❌ 解が見つかりませんでした")

