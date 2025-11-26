---
title: "LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド"
emoji: "😸"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["ナレッジグラフ", "生成AI", "形式レイヤ", "LLM設計"]
published: false
---

# LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド（強化版）

本記事は前編「LLM と RAG 盲信への警鐘」の続編です。前編では、LLM/RAG の曖昧性、Safe/Unsafe の境界、そして「LLM に決定させないための外側のレイヤ」の必要性について解説しました。

後編となる本記事では、以下の 4 種のレイヤを **形式レイヤ（Formal Layer）** として扱い、  
中級エンジニアが実際に手を動かせるレベルまで落とし込みます。

- SQL（値レイヤ / Value Layer）
- KG（意味レイヤ / Semantic Layer）
- ルールエンジン（ポリシーレイヤ / Policy Layer）
- 制約ソルバ（最適化レイヤ / Optimization Layer）

---

## 形式レイヤとは何か

形式レイヤとは、**論理的・数学的・規則的に正しい結果を返す“決定性のある外部レイヤ”** の総称です。

本記事では 4 種の形式レイヤを扱います。

- **SQL = 値レイヤ（Value Layer）**
- **KG = 意味レイヤ（Semantic Layer）**
- **ルールエンジン = ポリシーレイヤ（Policy Layer）**
- **制約ソルバ = 最適化レイヤ（Optimization Layer）**

LLM/RAG の曖昧性を外側で補完し、安全なアーキテクチャを構築するための基盤です。

### 形式レイヤと意味レイヤの関係（他記事との整合性）

既存記事「RAG を超える知識統合」では、KG を **意味レイヤ（Semantic Layer）** として扱っています。本記事はその立場を継承しつつ、意味レイヤを形式レイヤの構成要素の 1 つとして整理します。

---

# 1. SQL：値の一貫性を保証するレイヤ（Value Layer）

SQL は AI 時代でも最強の形式レイヤです。理由は以下のとおりです。

- PRIMARY KEY / UNIQUE / CHECK / FK による整合性保証
- ACID トランザクション
- 厳密なスキーマ
- インデックス / VIEW / 関数

LLM と真逆の性質を持つ、**曖昧さゼロの厳密な世界**を構築できます。

### SQL と LLM の分担

| 領域           | SQL の責任     | LLM の責任           |
| -------------- | -------------- | -------------------- |
| 金額 / 在庫    | 正しい値の保持 | 説明や要約           |
| 請求ステータス | 状態の正確性   | 状態の自然文での説明 |

LLM に値を“推測させる”のは危険です。

---

### ハンズオン：最小構成の SQL 実装

#### 事前準備

```
npm init -y
npm install better-sqlite3 @types/better-sqlite3
sqlite3 billing.db < schema.sql
```

#### schema.sql

```sql
CREATE TABLE billing (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open', 'closed'))
);
```

#### app.ts

```ts
import Database from "better-sqlite3";

type BillingQuery = {
  customerId: string;
  mode: "open" | "all";
};

const db = new Database("billing.db");

function runQuery(q: BillingQuery) {
  if (q.mode === "open") {
    return db
      .prepare(
        "SELECT id, amount, status FROM billing WHERE customer_id = ? AND status='open'"
      )
      .all(q.customerId);
  }
  return db
    .prepare("SELECT id, amount, status FROM billing WHERE customer_id = ?")
    .all(q.customerId);
}

const fromLlm: BillingQuery = { customerId: "CUST-123", mode: "open" };
console.log(runQuery(fromLlm));
```

ポイント：  
**LLM は BillingQuery 型だけ返し、SQL はアプリ側で安全に決定します。**

---

# 2. Knowledge Graph（KG）：意味レイヤ（Semantic Layer）

## KG が必要とされる理由（概要）

KG の詳細な理解は「RAG を超える知識統合」で解説しています。  
本記事では KG を形式レイヤの中の **意味レイヤ**として扱い、

- 顧客 → 契約 → プラン → SLA
- Issue → 機能 → 影響範囲

などの **意味構造と関係推論を外部で管理する役割** に絞ります。

---

## ハンズオン：Neo4j + Cypher の最小例

#### 事前準備（Docker）

```
docker run -p 7474:7474 -p 7687:7687 neo4j:5
```

ブラウザで http://localhost:7474 を開く。

#### モデル定義

```cypher
CREATE (:Customer {id:"CUST-123"})-[:HAS_CONTRACT]->
  (:Contract {id:"CON-1"})-[:ON_PLAN]->
  (:Plan {name:"Enterprise"})-[:HAS_SLA]->
  (:SLA {priority:"High"});
```

#### クエリ例

```cypher
MATCH (c:Customer {id: "CUST-123"})-[:HAS_CONTRACT]->(:Contract)-[:ON_PLAN]->(:Plan)-[:HAS_SLA]->(s:SLA)
RETURN s.priority;
```

ポイント：  
**KG 内部 ID を LLM に見せない。クエリはテンプレ化し、LLM は経路候補だけ出す。**

---

# 3. ルールエンジン：ポリシーレイヤ（Policy Layer）

アクセス制御 / 優先度判定 / 承認フローなど、誤ると問題になる判断ロジックは LLM に任せるべきではありません。

LLM は「適用するルールセット」を判定するだけにします。

---

## ハンズオン：OPA（Open Policy Agent）の最小例

#### OPA バイナリ

https://www.openpolicyagent.org/docs/

#### sla.rego

```rego
package sla
default priority = "Low"

priority = "High" {
  input.customer_tier == "Platinum"
  input.issue == "Critical"
}
```

#### input.json

```json
{
  "customer_tier": "Platinum",
  "issue": "Critical"
}
```

#### 実行

```
opa eval -i input.json -d sla.rego "data.sla.priority"
```

---

# 4. 制約ソルバ：最適化レイヤ（Optimization Layer）

スケジューリング、割り当て、リソース最適化は LLM が最も苦手とする領域です。  
LLM は **制約候補を JSON 化**させ、最適化はソルバに任せます。

---

## ハンズオン：OR-Tools の最小例

```
pip install ortools
```

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()
agents = ["A","B"]
tasks = ["T1","T2","T3"]

x={}
for i,a in enumerate(agents):
  for j,t in enumerate(tasks):
    x[(i,j)] = model.NewBoolVar(f"x_{a}_{t}")

for j,_ in enumerate(tasks):
  model.Add(sum(x[(i,j)] for i,_ in enumerate(agents)) == 1)

for i,_ in enumerate(agents):
  model.Add(sum(x[(i,j)] for j,_ in enumerate(tasks)) <= 2)

solver = cp_model.CpSolver()
solver.Solve(model)

for i,a in enumerate(agents):
  for j,t in enumerate(tasks):
    if solver.Value(x[(i,j)]) == 1:
      print(f"{a} -> {t}")
```

---

# 形式レイヤ 4 種の比較表

| レイヤ | 役割           | 守るもの         | 向いている領域   | LLM の役割           |
| ------ | -------------- | ---------------- | ---------------- | -------------------- |
| SQL    | 値の整合性保持 | 金額・在庫・残高 | 台帳、請求       | クエリ種別選択と説明 |
| KG     | 意味構造の保持 | 関係性・推論     | 顧客 → 契約 →SLA | 経路説明・候補生成   |
| ルール | 判断の厳密化   | ポリシー/SLA     | 優先度判定       | ルールセット選択     |
| ソルバ | 最適解探索     | 割り当て最適性   | スケジューリング | 制約抽出と説明       |

---

### まとめ

LLM は **入口（自然言語 → 構造化）と出口（構造化 → 自然言語）** に最適です。  
判断・整合性・推論・最適化は形式レイヤが担うことで、安全で拡張性のある AI システムを構築できます。

---

### 参考文献

- Zenn: ナレッジグラフ入門  
  https://zenn.dev/knowledge_graph/articles/knowledge-graph-intro
- Zenn: RAG なしで始めるナレッジグラフ QA  
  https://zenn.dev/knowledge_graph/articles/kg-no-rag-starter
- Zenn: GenAI Divide とナレッジグラフ  
  https://zenn.dev/knowledge_graph/articles/genai-divide-knowledge-graph
- Zenn: RAG を超える知識統合  
  https://zenn.dev/knowledge_graph/articles/beyond-rag-knowledge-graph
- Zenn: MCP の課題とナレッジグラフ  
  https://zenn.dev/knowledge_graph/articles/mcp-knowledge-graph
- Hallucination Survey (2024)  
  https://arxiv.org/abs/2311.05232
- Retrieval-Augmented Generation Survey (2025)  
  https://link.springer.com/article/10.1007/s00521-025-11666-9

### 更新履歴

- 2025-11-25 — 初版作成
- 2025-11-26 — ハンズオン拡充・比較表・文体統一を実施

### 注記

本記事は AI を活用して執筆しています。  
ご意見・修正提案は Zenn のコメントへお願いします。
