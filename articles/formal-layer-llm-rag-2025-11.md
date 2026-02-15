---
title: "LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド"
emoji: "😸"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["ナレッジグラフ", "生成AI", "形式レイヤ", "LLM設計"]
published: true
---

# LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド

本記事は前編[「LLM と RAG 盲信への警鐘」](https://zenn.dev/knowledge_graph/articles/rag-warning-2025-11)の続編です。

前編では、LLM/RAG の曖昧性、Safe/Unsafe の境界、そして「LLM に決定させないための外側のレイヤ」の必要性について解説しました。

先週 AWS re:Invent 2025 に参加し、Bedrock AgentCore の Policy Controls や
AgentCore Evaluations を中心に、LLM の曖昧性を外側のレイヤで制御する動きが
クラウドレベルで実装され始めていることを確認しました。

本記事では、その知見も踏まえながら LLM/RAG の曖昧性を抑える
「形式レイヤ（Formal Layer）」の具体的な実装ガイドを整理していきます。

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

### 形式レイヤと意味レイヤの関係

既存記事[「RAG を超える知識統合」](https://zenn.dev/articles/beyond-rag-knowledge-graph/)では、KG を **意味レイヤ（Semantic Layer）** として扱っています。本記事はその立場を継承しつつ、意味レイヤを形式レイヤの構成要素の 1 つとして整理します。

---

# 1. SQL：値の一貫性を保証するレイヤ（Value Layer）

SQL は AI 時代でも最強の形式レイヤです。理由は以下のとおりです。

- PRIMARY KEY / UNIQUE / CHECK / FK による整合性保証
- ACID トランザクション
- 厳密なスキーマ
- インデックス / VIEW / 関数

LLM と比べて**極めて高い決定性を持つ厳密な世界**を構築できます。

### SQL と LLM の分担

| 領域           | SQL の責任     | LLM の責任           |
| -------------- | -------------- | -------------------- |
| 金額 / 在庫    | 正しい値の保持 | 説明や要約           |
| 請求ステータス | 状態の正確性   | 状態の自然文での説明 |

LLM に値を“推測させる”のは危険です。

---

### SQL レイヤを使うメリット

**なぜ SQL レイヤを使うのか？**

- **SQL インジェクションのリスク低減**: LLM が生成した SQL 文字列をそのまま実行するのではなく、LLM は構造化されたクエリパラメータ（`BillingQuery` 型）のみを返し、SQL はアプリ側でパラメータ化クエリとして安全に構築されます
- **型安全性の保証**: TypeScript の型システムにより、LLM が返すデータ構造がコンパイル時に検証されます
- **整合性の自動保証**: CHECK 制約や FOREIGN KEY により、データベースレベルで整合性が保証されます

※課題: スキーマ設計やマイグレーションのコストが高く、要件変更のたびに DB 設計とアプリケーションの両方を更新する必要があります。

**使うとどうなるのか？**

- LLM は自然言語から `{"customerId": "CUST-123", "mode": "open"}` のような構造化データを抽出するだけ
- アプリ側で `WHERE customer_id = ?` のようなパラメータ化クエリを実行
- `OR 1=1` のような SQL インジェクション攻撃は物理的に不可能

#### 最小構成の実装例

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
```

**詳細な実装手順や動作確認方法は、[実験環境の README](https://github.com/DevRev-JP/tech-blog/tree/main/experiments/formal-layer#1-sql値レイヤ) を参照してください。**

---

# 2. Knowledge Graph（KG）：意味レイヤ（Semantic Layer）

## KG が必要とされる理由（概要）

KG の詳細な理解は[「RAG を超える知識統合」](https://zenn.dev/knowledge_graph/articles/beyond-rag-knowledge-graph)で解説しています。  
本記事では KG を形式レイヤの中の **意味レイヤ**として扱い、

- 顧客 → 契約 → プラン → SLA
- Issue → 機能 → 影響範囲

などの **意味構造と関係推論を外部で管理する役割** に絞ります。

---

### KG レイヤを使うメリット

**なぜ KG レイヤを使うのか？**

- **関係推論の決定性**: RAG の「似ている文書を返す」ではなく、「顧客 → 契約 → プラン → SLA」のような明確な関係性に基づいて推論できます
- **内部 ID の隠蔽**: KG の内部 ID を LLM に見せず、経路テンプレート（`sla`, `contract`, `plan` など）だけを選択させることで、セキュリティリスクを低減します
- **意味構造の明示**: 関係性がグラフとして明示されるため、推論の根拠が追跡可能です

※課題: ドメインモデリングと運用の初期コストが高く、小規模なユースケースではオーバーエンジニアリングになりがちです。

**使うとどうなるのか？**

- LLM は自然言語から経路タイプ（`{"path_type": "sla"}`）を選択するだけ
- KG レイヤが経路テンプレートに基づいて Cypher クエリを実行
- 結果として、RAG の「似ている文書」ではなく、「確実に関係性が存在するデータ」のみが返されます

#### 最小構成の実装例

```cypher
// モデル定義: 顧客 → 契約 → プラン → SLA の関係を明示
CREATE (:Customer {id:"CUST-123"})-[:HAS_CONTRACT]->
  (:Contract {id:"CON-1"})-[:ON_PLAN]->
  (:Plan {name:"Enterprise"})-[:HAS_SLA]->
  (:SLA {priority:"High"});

// クエリ: 経路テンプレートに基づく決定性のある推論
MATCH (c:Customer {id: "CUST-123"})-[:HAS_CONTRACT]->(:Contract)-[:ON_PLAN]->(:Plan)-[:HAS_SLA]->(s:SLA)
RETURN s.priority;
```

**詳細な実装手順や動作確認方法は、[実験環境の README](https://github.com/DevRev-JP/tech-blog/tree/main/experiments/formal-layer#2-kg意味レイヤ) を参照してください。**

---

# 3. ルールエンジン：ポリシーレイヤ（Policy Layer）

アクセス制御 / 優先度判定 / 承認フローなど、誤ると問題になる判断ロジックは LLM に任せるべきではありません。

**ポリシーは外部で定義（OPA Rego ファイル）し、外部レイヤが監視・強制します。**  
LLM は自然言語からポリシー評価用の入力データ（`customer_tier`, `issue` など）を抽出するだけです。

---

### ポリシーレイヤを使うメリット

**なぜポリシーレイヤを使うのか？**

- **ポリシーの外部化**: if/else ベタ書きではなく、OPA Rego ファイルとして外部化することで、コード変更なしでポリシーを更新できます
- **検証可能性**: ポリシーが外部ファイルとして定義されるため、監査や検証が容易になります
- **決定性の保証**: LLM が「おそらく High 優先度」と推測するのではなく、OPA が入力データに基づいて確定的に判定します

※課題: Rego などのポリシー言語の学習コストがあり、非エンジニアが直接扱うにはハードルが高い場合があります。

**使うとどうなるのか？**

- LLM は自然言語から `{"customer_tier": "Platinum", "issue": "Critical"}` のような入力データを抽出するだけ
- OPA が Rego ポリシーに基づいて確定的に優先度を判定（例: `Platinum + Critical → High`）
- ポリシー変更時は Rego ファイルを更新するだけで、コード変更やデプロイが不要

#### 最小構成の実装例

```rego
package sla
default priority = "Low"

priority = "High" if {
  input.customer_tier == "Platinum"
  input.issue == "Critical"
}
```

**詳細な実装手順や動作確認方法は、[実験環境の README](https://github.com/DevRev-JP/tech-blog/tree/main/experiments/formal-layer#3-ルールエンジンポリシーレイヤ) を参照してください。**

---

# 4. 制約ソルバ：最適化レイヤ（Optimization Layer）

スケジューリング、割り当て、リソース最適化は LLM が最も苦手とする領域です。  
LLM は **制約候補を JSON 化**させ、制約充足問題（CSP）の解決はソルバに任せます。

---

### 制約ソルバを使うメリット

**なぜ制約ソルバを使うのか？**

- **組合せ爆発の解決**: LLM が「おそらく Agent1 に割り当てるのが良さそう」と推測するのではなく、制約充足問題（CSP）として数学的に解決します
- **実行可能性の保証**: 制約を満たす解が存在する場合、必ず実行可能な解を見つけます
- **再現性**: 同じ制約と入力に対して、常に同じ解（または同等の解）を返します

※課題: 制約モデルの設計が難しく、大規模問題では計算資源とチューニングコストが無視できません。

**使うとどうなるのか？**

- LLM は自然言語から制約を抽出（例: `{"agents": ["A", "B"], "tasks": ["T1", "T2", "T3"], "max_tasks_per_agent": 2}`）
- OR-Tools が制約充足問題として解決
- 結果として、LLM の「推測」ではなく、数学的に保証された実行可能な割り当てが得られます

#### 最小構成の実装例

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()
agents = ["A","B"]
tasks = ["T1","T2","T3"]

x={}
for i,a in enumerate(agents):
  for j,t in enumerate(tasks):
    x[(i,j)] = model.NewBoolVar(f"x_{a}_{t}")

# 各タスクは必ず1つのエージェントに割り当てられる
for j,_ in enumerate(tasks):
  model.Add(sum(x[(i,j)] for i,_ in enumerate(agents)) == 1)

# 各エージェントは最大2つのタスクを処理できる
for i,_ in enumerate(agents):
  model.Add(sum(x[(i,j)] for j,_ in enumerate(tasks)) <= 2)

solver = cp_model.CpSolver()
solver.Solve(model)
```

**詳細な実装手順や動作確認方法は、[実験環境の README](https://github.com/DevRev-JP/tech-blog/tree/main/experiments/formal-layer#4-制約ソルバ最適化レイヤ) を参照してください。**

---

# 形式レイヤ 4 種の比較表

| レイヤ | 役割               | 守るもの             | 向いている領域   | LLM の役割           |
| ------ | ------------------ | -------------------- | ---------------- | -------------------- |
| SQL    | 値の整合性保持     | 金額・在庫・残高     | 台帳、請求       | クエリ種別選択と説明 |
| KG     | 意味構造の保持     | 関係性・推論         | 顧客 → 契約 →SLA | 経路説明・候補生成   |
| ルール | 判断の厳密化       | ポリシー/SLA         | 優先度判定       | 入力データ抽出       |
| ソルバ | 制約充足問題の解決 | 割り当ての実行可能性 | スケジューリング | 制約抽出と説明       |

---

### まとめ

LLM は **入口（自然言語 → 構造化）と出口（構造化 → 自然言語）** に最適です。  
判断・整合性・推論・制約充足は形式レイヤが担うことで、安全で拡張性のある AI システムを構築できます。

---

## 実験環境：実際に手を動かして確認する

本記事で紹介した 4 つの形式レイヤを実際に動作確認できる Docker ベースの実験環境を用意しています。

**実験環境**: [GitHub リポジトリ](https://github.com/DevRev-JP/tech-blog/tree/main/experiments/formal-layer)

### 実験環境を使うメリット

**なぜ実験環境を使うのか？**

- **実際の動作を確認できる**: 記事の概念をコードレベルで体験し、「なぜ形式レイヤが必要なのか」を実感できます
- **安全な実装と危険な実装を比較できる**: 形式レイヤを使う場合と使わない場合の違いを、実際に動作させて比較できます
- **統合シナリオで一気通貫のフローを体験できる**: 4 つの形式レイヤが連携する実際のフローを、エンドツーエンドで確認できます

※課題: Docker / Neo4j / OPA など複数コンポーネントのセットアップが必要で、ローカル環境によってはリソース消費や起動時間が問題になることがあります。

**使うとどうなるのか？**

- **SQL インジェクションのリスクを実感**: アンチパターン例で SQL インジェクションの危険性を実際に確認できます
- **ポリシー変更の容易さを体験**: OPA Rego による外部化と、if/else ベタ書きの違いを比較できます
- **LLM の役割が明確になる**: LLM が「入口（自然言語 → 構造化）と出口（構造化 → 自然言語）」のみを担当することを、実際のコードで確認できます

### 実験環境の構成

- **4 つの形式レイヤ API**: SQL Layer、KG Layer、Policy Layer、Optimization Layer
- **アンチパターン例**: LLM に直接 SQL を書かせたり、if/else ベタ書きのポリシーなど、危険な実装例
- **LLM モック**: 自然言語から構造化データへの変換例
- **統合シナリオ**: 顧客サポートフローを 4 レイヤで一気通貫で処理する例

**詳細なセットアップ手順、API エンドポイント、トラブルシューティングなどは、[実験環境の README](https://github.com/DevRev-JP/tech-blog/tree/main/experiments/formal-layer) を参照してください。**

---

# AWS AgentCore に見る形式レイヤのクラウド実装（AWS re:Invent 2025）

## Policy Controls（Cedar によるポリシーレイヤ）

AWS re:Invent 2025 では、Amazon Bedrock AgentCore に Policy Controls が追加され、
エージェントによるツール実行の境界を Cedar ポリシー言語で厳密に制御できるようになりました。

- 「慎重なプロンプト設計」だけでは防ぎきれない誤動作を防止
- 自然言語で「$1,000 を超える返金はブロックして」と指定すると内部で Cedar が生成
- Runtime → Gateway → Tool の実行経路でミリ秒単位のポリシー検証
- LLM は提案のみを担い、最終判断は Cedar が実施

### Cedar による実際のポリシー例

```
permit (
  principal == AgentCore::OAuthUser,
  action == AgentCore::Action::"InsuranceAPI__file_claim",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:..."
)
when { context.input.has refundAmount && context.input.refundAmount < 1000 };
```

---

## AgentCore Evaluations（品質レイヤ）

AgentCore では Evaluations が導入され、エージェントの実世界の行動を継続的に検査できます。

- 正確性、有用性、ツール選択精度、安全性など 13 種類の評価指標を標準提供
- カスタム評価モデルやプロンプトも利用可能
- 例：8 時間で満足度スコアが 10% 下落した場合は即アラート
- 品質問題を顧客影響前に検知し、迅速な対応が可能

形式レイヤが「決定の正しさ」を保証し、Evaluations が「挙動の品質」を監視する構造となる。

---

## Automated Reasoning（自動推論と形式レイヤの親和性）

AWS が長年推進してきた Automated Reasoning（形式手法）は、形式レイヤの思想と本質的に一致します。

- ユークリッドの数学証明と同じ厳密性でプログラムの全状態を検証
- LLM の「おそらく正しい」という統計的性質に対し、「確実に正しい」ことを保証
- 以下のような分野で実績：
  - Kiro：仕様駆動開発
  - Cedar：AgentCore におけるポリシー検証
  - Smithy：API 形式化言語で API 整合性を検証

---

## Agentic Teammates（AI エージェントを“チームメイト”として扱う思想）

re:Invent では「AI エージェントは人間のチームメイトになる」というメッセージが強調されました。

- 真の企業変革は AI を日常業務に自然に組み込むことにある
- AI は自動化にとどまらず、新製品開発・サービス改善・新規ビジネス創出に寄与
- 技術よりも「人間の想像力」が最大の制約となる
- Amazon Connect の事例では AI ネイティブな顧客サービスが世界的に運用されている
- AI は完璧を待つのではなく、実践を通じた継続的改善が重要

これらの発表は、LLM に決定を委ねず、外側の形式レイヤが行動を制御するという本記事の主張を強く裏づけています。

---

### 参考文献

- Zenn: ナレッジグラフ入門  
  https://zenn.dev/knowledge_graph/articles/knowledge-graph-intro
- Zenn: RAG なしで始めるナレッジグラフ QA  
  https://zenn.dev/knowledge_graph/articles/kg-no-rag-starter
- Zenn: GenAI Divide とナレッジグラフ  
  https://zenn.dev/articles/genai-divide-knowledge-graph
- Zenn: RAG を超える知識統合  
  https://zenn.dev/knowledge_graph/articles/beyond-rag-knowledge-graph
- Zenn: MCP の課題とナレッジグラフ  
  https://zenn.dev/knowledge_graph/articles/mcp-knowledge-graph
- Cedar Policy Language — Specification and Developer Guide  
  https://www.cedarpolicy.com/
- Cedar: Fast, Safe, and Analyzable Authorization  
  https://github.com/cedar-policy/cedar
- Amazon Bedrock AgentCore Adds Quality Evaluations and Policy Controls for Deploying Trusted AI Agents  
  https://aws.amazon.com/jp/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/

### 更新履歴

- 2025-12-09 — 初版作成

### 注記

本記事は AI を活用して執筆しています。  
ご意見・修正提案は Zenn のコメントへお願いします。
