# 形式レイヤ（Formal Layer）実験環境

このディレクトリは、「LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド」のサンプル実装です。記事で述べた 4 つの形式レイヤを、実際に Docker で動作確認できます。

**記事**: https://zenn.dev/knowledge_graph/articles/formal-layer-llm-rag-2025-11

---

## 📖 記事との対応関係

この実験環境は、記事の以下のセクションに対応しています：

| 記事のセクション                                 | 実装場所                         | 説明                                     |
| ------------------------------------------------ | -------------------------------- | ---------------------------------------- |
| **1. SQL：値の一貫性を保証するレイヤ**           | `sql-layer/`                     | API サービスとして実装                   |
| **ハンズオン：最小構成の SQL 実装**              | `examples/sql-minimal/`          | 記事の例をそのまま実行可能               |
| **2. Knowledge Graph（KG）：意味レイヤ**         | `kg-layer/`                      | API サービスとして実装                   |
| **ハンズオン：Neo4j + Cypher の最小例**          | `examples/kg-minimal/`           | 記事の例をそのまま実行可能               |
| **3. ルールエンジン：ポリシーレイヤ**            | `policy-layer/`                  | API サービスとして実装                   |
| **ハンズオン：OPA（Open Policy Agent）の最小例** | `examples/policy-minimal/`       | 記事の例をそのまま実行可能               |
| **4. 制約ソルバ：最適化レイヤ**                  | `optimization-layer/`            | API サービスとして実装                   |
| **ハンズオン：OR-Tools の最小例**                | `examples/optimization-minimal/` | 記事の例をそのまま実行可能               |
| **統合シナリオ**                                 | `end-to-end.sh`                  | 4 つの形式レイヤを連携した一気通貫フロー |
| **アンチパターン例**                             | `naive/`                         | 形式レイヤを使わない危険な実装例         |

### 使い分け

- **`examples/`**: 記事のハンズオンセクションで説明されている最小構成を、そのまま実行できるスタンドアロン例
- **各レイヤの API サービス**: 実際の本番環境で使用する API サービス実装
- **`end-to-end.sh`**: 4 つの形式レイヤを連携した統合シナリオ

---

## 🎯 実験の目的

LLM/RAG の曖昧性を抑えるために、**決定性のある外部レイヤ**として 4 つの形式レイヤを実装しています。

- **SQL（値レイヤ）**: 金額・在庫・残高などの値の整合性を保証
- **KG（意味レイヤ）**: 顧客 → 契約 → プラン → SLA などの意味構造と関係推論
- **ルールエンジン（ポリシーレイヤ）**: アクセス制御・優先度判定・承認フローの厳密化
- **制約ソルバ（最適化レイヤ）**: スケジューリング・割り当て・リソース最適化

### 💡 設計意図

この実装では以下の構成になっています：

- **各形式レイヤは独立した API サービス**として実装
- **LLM は入口（自然言語 → 構造化）と出口（構造化 → 自然言語）のみを担当**
- **判断・整合性・推論・制約充足は形式レイヤが決定性を持って実行**

**なぜこの構成か？** — 読者が「**LLM の曖昧性を外側の形式レイヤで制御する**」という思想を理解するための最小構成です。

---

## 📋 実験の構成

### 形式レイヤ 4 種の比較

| レイヤ | 役割               | 守るもの             | 向いている領域   | LLM の役割           |
| ------ | ------------------ | -------------------- | ---------------- | -------------------- |
| SQL    | 値の整合性保持     | 金額・在庫・残高     | 台帳、請求       | クエリ種別選択と説明 |
| KG     | 意味構造の保持     | 関係性・推論         | 顧客 → 契約 →SLA | 経路説明・候補生成   |
| ルール | 判断の厳密化       | ポリシー/SLA         | 優先度判定       | ルールセット選択     |
| ソルバ | 制約充足問題の解決 | 割り当ての実行可能性 | スケジューリング | 制約抽出と説明       |

---

## 🏗 コンテナ構成

| サービス名           | 役割                            | ポート |
| -------------------- | ------------------------------- | ------ |
| `sql-layer`          | SQL 値レイヤ API（Express）     | 8300   |
| `kg-layer`           | KG 意味レイヤ API（FastAPI）    | 8400   |
| `policy-layer`       | ルールエンジン API（FastAPI）   | 8500   |
| `optimization-layer` | 制約ソルバ API（FastAPI）       | 8600   |
| `llm-mock`           | LLM モック API（FastAPI）       | 8700   |
| `neo4j`              | ナレッジグラフ DB（KG 用）      | 7474   |
| `opa`                | Open Policy Agent（ポリシー用） | 8181   |

---

## 🚀 クイックスタート

### 前提

- macOS（または Linux/WSL2）
- Docker / Docker Compose v2
- `curl` コマンド
- `jq` コマンド（オプション、JSON の整形用）

### 方法 1: 記事のハンズオン例を実行する（最小構成）

記事のハンズオンセクションで説明されている最小構成を、そのまま実行できます：

```bash
cd experiments/formal-layer/examples

# SQL の最小構成
cd sql-minimal
npm install && npm run setup && npm start

# KG の最小構成（Neo4j が必要）
cd ../kg-minimal
pip install -r requirements.txt
python seed.py    # データのシード
python query.py   # クエリの実行

# ポリシーの最小構成（OPA が必要）
cd ../policy-minimal
# OPA サーバーを起動してから
python query.py

# 最適化の最小構成
cd ../optimization-minimal
pip install -r requirements.txt
python solve.py
```

詳細は `examples/README.md` を参照してください。

### 方法 2: API サービスとして実行する（統合環境）

4 つの形式レイヤを API サービスとして起動し、統合シナリオを実行できます：

```bash
cd experiments/formal-layer

# 初回ビルドと起動
docker compose up --build -d

# 初期化完了まで待機（約 30-60 秒）
sleep 60

# ヘルスチェック
curl -sf http://localhost:8300/healthz  # SQL Layer
curl -sf http://localhost:8400/healthz  # KG Layer
curl -sf http://localhost:8500/healthz  # Policy Layer
curl -sf http://localhost:8600/healthz  # Optimization Layer
curl -sf http://localhost:8700/healthz  # LLM Mock
```

### 統合シナリオの実行

4 つの形式レイヤを連携させた一気通貫のフローを実行できます：

```bash
# 統合シナリオ: 顧客サポートフロー
./end-to-end.sh

# カスタム入力で実行
./end-to-end.sh "CUST-456 の全請求を見せて" "重要なお客様にとって重要度が高い問題"
```

---

## 📊 各形式レイヤの使い方

### 1. SQL（値レイヤ）

**役割**: 金額・在庫・残高などの値の整合性を保証

#### 例: 請求データのクエリ

```bash
# 特定顧客の未処理請求を取得
curl -X POST http://localhost:8300/query \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "CUST-123",
    "mode": "open"
  }' | jq

# 全請求を取得
curl -X POST http://localhost:8300/query \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": "CUST-123",
    "mode": "all"
  }' | jq
```

**ポイント**: LLM は `BillingQuery` 型（`customerId`, `mode`）だけ返し、SQL はアプリ側で安全に決定します。

---

### 2. KG（意味レイヤ）

**役割**: 顧客 → 契約 → プラン → SLA などの意味構造と関係推論

#### 例: 顧客の SLA 優先度を取得

```bash
# 利用可能な経路テンプレートを確認
curl http://localhost:8400/paths | jq

# 顧客のSLA情報を取得（経路: Customer -> Contract -> Plan -> SLA）
curl -X POST http://localhost:8400/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-123",
    "path_type": "sla"
  }' | jq

# 契約情報のみを取得（経路: Customer -> Contract）
curl -X POST http://localhost:8400/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-123",
    "path_type": "contract"
  }' | jq

# プラン情報まで取得（経路: Customer -> Contract -> Plan）
curl -X POST http://localhost:8400/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-123",
    "path_type": "plan"
  }' | jq

# 全情報を取得（経路: Customer -> Contract -> Plan -> SLA）
curl -X POST http://localhost:8400/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-123",
    "path_type": "full"
  }' | jq

# グラフ全体を確認
curl http://localhost:8400/graph | jq
```

**ポイント**:

- KG 内部 ID を LLM に見せない。クエリはテンプレ化し、LLM は経路候補だけ出します。
- 経路テンプレートは外部（KG Layer）で定義され、`GET /paths` で一覧を取得できます。
- LLM は自然言語から適切な経路タイプを選択します（`LLM Mock: POST /extract-kg-path` を参照）。

**Neo4j ブラウザ**: http://localhost:7474 (neo4j/password)

---

### 3. ルールエンジン（ポリシーレイヤ）

**役割**: アクセス制御・優先度判定・承認フローの厳密化

#### 例: SLA 優先度の判定

```bash
# 顧客ティアと課題の重要度からSLA優先度を判定
curl -X POST http://localhost:8500/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "customer_tier": "Platinum",
    "issue": "Critical"
  }' | jq

# 別の例
curl -X POST http://localhost:8500/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "customer_tier": "Platinum",
    "issue": "High"
  }' | jq
```

**ポイント**: LLM は「適用するルールセット」を判定するだけにします。最終判断は OPA が実施します。

**OPA ポリシー**: `policy-layer/policies/sla.rego`

---

### 4. 制約ソルバ（最適化レイヤ）

**役割**: スケジューリング・割り当て・リソース最適化

#### 例: タスク割り当て問題

```bash
# タスクをエージェントに割り当て
curl -X POST http://localhost:8600/assign \
  -H "Content-Type: application/json" \
  -d '{
    "agents": ["A", "B"],
    "tasks": ["T1", "T2", "T3"],
    "max_tasks_per_agent": 2
  }' | jq

# サンプル実行（記事の例）
curl -X POST http://localhost:8600/schedule | jq
```

**ポイント**: LLM は制約候補を JSON 化させ、制約充足問題（CSP）の解決は OR-Tools ソルバに任せます。

---

## 🔧 API エンドポイント

### SQL Layer (Port 8300)

- `GET /healthz` - ヘルスチェック
- `POST /query` - 請求データのクエリ
- `GET /billing` - 全請求データの取得

### KG Layer (Port 8400)

- `GET /healthz` - ヘルスチェック
- `POST /query` - ナレッジグラフのクエリ
- `GET /graph` - グラフ全体の取得

### Policy Layer (Port 8500)

- `GET /healthz` - ヘルスチェック
- `POST /evaluate` - ポリシー評価
- `GET /policies` - 利用可能なポリシー一覧

### Optimization Layer (Port 8600)

- `GET /healthz` - ヘルスチェック
- `POST /assign` - タスク割り当て問題の解決
- `POST /schedule` - サンプルスケジューリング

### LLM Mock (Port 8700)

- `GET /healthz` - ヘルスチェック
- `POST /extract-billing-query` - 自然言語から請求クエリを抽出
- `POST /extract-policy-request` - 自然言語からポリシーリクエストを抽出
- `POST /format-response` - 構造化データから自然言語の応答を生成

---

## 🤖 LLM モック: 自然言語 ↔ 構造化データの変換

LLM の役割を理解するために、自然言語から構造化データへの変換例を提供しています。

### 自然言語から構造化データへの変換

```bash
# 請求クエリの抽出
curl -X POST http://localhost:8700/extract-billing-query \
  -H "Content-Type: application/json" \
  -d '{"text": "CUST-123 の未処理請求を取得して"}' | jq

# ポリシーリクエストの抽出
curl -X POST http://localhost:8700/extract-policy-request \
  -H "Content-Type: application/json" \
  -d '{"text": "プラチナ顧客のクリティカルな問題"}' | jq

# KG 経路タイプの抽出（自然言語から経路候補を選択）
curl -X POST http://localhost:8700/extract-kg-path \
  -H "Content-Type: application/json" \
  -d '{"text": "顧客のSLA情報が知りたい"}' | jq

# 構造化データから自然言語への変換
curl -X POST http://localhost:8700/format-response \
  -H "Content-Type: application/json" \
  -d '{"priority": "High", "customer_id": "CUST-123"}' | jq
```

**ポイント**: 実際の実装では、OpenAI API や Anthropic API などを使用します。  
このモックは、LLM が「入口（自然言語 → 構造化）と出口（構造化 → 自然言語）」のみを担当することを示しています。

---

## ⚠️ アンチパターン例: 形式レイヤを使わない危険な実装

**形式レイヤを使う場合と使わない場合の違い**を理解するために、危険な実装例を用意しています。

### SQL インジェクションのリスク

```bash
# アンチパターン: LLM に直接 SQL を書かせてしまう
cd naive/sql-unsafe
docker compose up -d

# 危険: LLM が生成した SQL をそのまま実行
curl -X POST http://localhost:8800/execute \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM billing WHERE customer_id = '\''CUST-123'\'' OR 1=1"}'
```

**問題点**:

- SQL インジェクションのリスク
- 意図しないデータ操作（DELETE, DROP など）
- 型安全性の欠如

**正しい実装**: SQL Layer では、LLM は `BillingQuery` 型だけ返し、SQL はアプリ側で安全に決定します。

### if/else ベタ書きのポリシー

```bash
# アンチパターン: if/else ベタ書きのポリシー判定
cd naive/policy-unsafe
docker compose up -d

# 危険: ポリシーロジックがコードに埋め込まれている
curl -X POST http://localhost:8900/evaluate \
  -H "Content-Type: application/json" \
  -d '{"customer_tier": "Platinum", "issue": "Critical"}'
```

**問題点**:

- ポリシーの変更にコード変更が必要
- 複雑な条件の組み合わせでバグが発生しやすい
- 監査や検証が困難

**正しい実装**: Policy Layer では、OPA を使用してポリシーを外部化し、厳密に検証できます。

---

## 📈 統合シナリオ: LLM + 形式レイヤの連携

### 一気通貫フロー: 顧客サポートの優先度判定

`end-to-end.sh` スクリプトを使用すると、4 つの形式レイヤが連携するフローを一気に実行できます：

```bash
./end-to-end.sh
```

このスクリプトは以下のフローを実行します：

1. **LLM**: 自然言語から構造化データを抽出

   - 「CUST-123 の未処理請求を取得して」→ `{"customerId": "CUST-123", "mode": "open"}`

2. **SQL Layer**: 顧客の契約情報を取得

   - 値の整合性を保証

3. **KG Layer**: 顧客の契約プランと SLA 情報を取得

   - **LLM**: 自然言語から経路タイプを選択（「顧客の SLA 情報が知りたい」→ `{"path_type": "sla"}`）
   - **KG Layer**: 経路テンプレートに基づいて Cypher クエリを実行
   - 意味構造と関係推論

4. **Policy Layer**: 顧客ティアと課題重要度から優先度を判定

   - 判断の厳密化

5. **Optimization Layer**: エージェントへの割り当てを最適化

   - 制約充足問題の解決

6. **LLM**: 構造化データから自然言語の応答を生成
   - 「CUST-123 の優先度は Medium です。Agent1 に割り当てました（未処理請求 1 件）。」

**このフローでは、LLM は自然言語 ↔ 構造化データの変換のみを担当し、判断・整合性・推論・制約充足は形式レイヤが決定性を持って実行します。**

---

## 🧪 評価スクリプト

### 個別レイヤのテスト

`evaluate.sh` スクリプトを使用すると、簡単に各形式レイヤをテストできます：

```bash
# 全レイヤのヘルスチェック
./evaluate.sh health

# SQL Layer のテスト
./evaluate.sh sql

# KG Layer のテスト
./evaluate.sh kg

# Policy Layer のテスト
./evaluate.sh policy

# Optimization Layer のテスト
./evaluate.sh optimization

# 全レイヤのテスト
./evaluate.sh all
```

### 統合シナリオの実行

```bash
# デフォルトのシナリオで実行
./end-to-end.sh

# カスタム入力で実行
./end-to-end.sh "CUST-456 の全請求を見せて" "重要なお客様にとって重要度が高い問題"
```

### アンチパターンとの比較

形式レイヤを使う場合と使わない場合の違いを比較できます：

```bash
# アンチパターン例を起動
cd naive
docker compose up --build -d
cd ..

# 安全な実装（形式レイヤ使用）
curl -X POST http://localhost:8300/query \
  -d '{"customerId": "CUST-123", "mode": "open"}'

# 危険な実装（アンチパターン: SQL インジェクションのリスク）
curl -X POST http://localhost:8800/execute \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM billing WHERE customer_id = '\''CUST-123'\'' OR 1=1"}'

# 危険な実装（アンチパターン: if/else ベタ書きのポリシー）
curl -X POST http://localhost:8900/evaluate \
  -H "Content-Type: application/json" \
  -d '{"customer_tier": "Platinum", "issue": "Critical"}'
```

**比較ポイント**:

| 観点             | 安全な実装（形式レイヤ使用）             | 危険な実装（アンチパターン）            | リスク                                                          |
| ---------------- | ---------------------------------------- | --------------------------------------- | --------------------------------------------------------------- |
| **SQL Layer**    | パラメータ化クエリ（`?` プレースホルダ） | LLM が生成した SQL 文字列をそのまま実行 | SQL インジェクション、意図しないデータ操作（DELETE, DROP など） |
| **Policy Layer** | OPA Rego による外部化・検証可能          | if/else ベタ書き                        | ポリシー変更にコード変更が必要、テスト困難、監査困難            |

### アンチパターンの実際のリスク例

#### SQL インジェクションの例

```bash
# 危険な実装: LLM が生成した SQL をそのまま実行
curl -X POST http://localhost:8800/execute \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM billing WHERE customer_id = '\''CUST-123'\'' OR 1=1"}'

# 結果: 全顧客のデータが漏洩する可能性
```

**安全な実装では**:

- LLM は `{"customerId": "CUST-123", "mode": "open"}` のような構造化データのみ返す
- SQL はアプリ側でパラメータ化クエリとして安全に構築される
- `OR 1=1` のような攻撃は物理的に不可能

#### ポリシー変更の困難さ

**危険な実装（if/else ベタ書き）**:

- ポリシー変更 → コード変更 → デプロイ → テストが必要
- 複雑な条件の組み合わせでバグが発生しやすい
- 監査や検証が困難

**安全な実装（OPA Rego）**:

- ポリシー変更 → Rego ファイルを更新 → OPA に再読み込み（コード変更不要）
- ポリシーは外部で定義され、検証可能
- 監査ログやポリシーのバージョン管理が容易

---

## 🔧 トラブルシューティング

**サービスが起動しない**

```bash
# ログを確認
docker compose logs sql-layer kg-layer policy-layer optimization-layer neo4j opa

# クリーンアップして再起動
docker compose down -v
docker compose up --build -d
sleep 60
```

**初期化が完了していない**

コンテナ起動後、データベース初期化に **約 30-60 秒** かかります。ヘルスチェックで確認してください：

```bash
curl -sf http://localhost:8300/healthz
curl -sf http://localhost:8400/healthz
curl -sf http://localhost:8500/healthz
curl -sf http://localhost:8600/healthz
```

**Neo4j に接続できない**

```bash
# Neo4j ブラウザで確認
open http://localhost:7474
# 認証情報: neo4j / password
```

**OPA ポリシーが読み込まれない**

```bash
# OPA の状態を確認
curl http://localhost:8181/v1/policies

# ポリシーを手動で再読み込み
docker compose restart policy-layer
```

---

## 📌 実装上の注意点

- **SQL Layer**: TypeScript + better-sqlite3 を使用。データは `/data/billing.db` に永続化されます。
- **KG Layer**: Neo4j を使用。起動時にサンプルデータを自動シードします（`Customer` / `Contract` / `Plan` / `SLA` ラベルを持つノードのみを初期化する想定です。専用の Neo4j コンテナでの利用を前提としてください）。
- **Policy Layer**: OPA を使用。`policies/sla.rego` が自動的に読み込まれます。
- **Optimization Layer**: OR-Tools を使用。制約充足問題（CSP）を解決します。
- **LLM Mock**: 実際の LLM API の代わりに、簡単なルールベースで自然言語を構造化データに変換します。実際の実装では、OpenAI API や Anthropic API などを使用します。

## 🎓 学習ポイント

この実験環境では、以下のポイントを学習できます：

1. **形式レイヤの役割**: 4 つの形式レイヤがそれぞれどのような問題を解決するか
2. **LLM の責務分離**: LLM は「入口（自然言語 → 構造化）と出口（構造化 → 自然言語）」のみを担当
3. **アンチパターンの危険性**: 形式レイヤを使わない場合のリスク（SQL インジェクション、ポリシーの複雑化など）
4. **統合フロー**: 複数の形式レイヤを連携させた一気通貫の処理フロー

---

## 📚 関連リンク

- 記事: [LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド](../../articles/formal-layer-llm-rag-2025-11.md)
- 前編: [LLM と RAG 盲信への警鐘](../../articles/rag-warning-2025-11.md)
- ハンズオン例: [examples/README.md](examples/README.md) - 記事の最小構成をそのまま実行
- Open Policy Agent: https://www.openpolicyagent.org/
- OR-Tools: https://developers.google.com/optimization
- Neo4j: https://neo4j.com/

---

## 📝 ライセンス

この実験環境は記事の読者向けに提供されています。各ライブラリのライセンスについては、それぞれのリポジトリを参照してください。
