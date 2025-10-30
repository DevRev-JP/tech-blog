# GraphRAG vs LightRAG 比較実験

このディレクトリは、「GraphRAG の限界と LightRAG の登場」のサンプル実装です。記事で述べた理論を、実際に Docker で動作確認できます。

**記事**: https://zenn.dev/knowledge_graph/articles/graphrag-light-rag-2025-10

---

## 🎯 実験の目的

GraphRAG と LightRAG を同じデータセットで比較し、**LightRAG がどのように改善したのか** を手元で再現できます。

- **軽量化**: 全体グラフではなくクエリ依存のサブグラフのみを探索
- **階層化**: ベクトル検索（低レベル）→ グラフ探索（高レベル）の二層検索
- **適応**: attention 重みによる逐次最適化（実験環境では手動フィードバック）

### 💡 設計意図

この実装では以下の構成になっています：

- **GraphRAG パイプライン**: 質問 → キーワード検索 → グラフ探索（簡易実装）
- **LightRAG パイプライン**: 質問 → ベクトル埋め込み（Qdrant）→ 局所グラフ構築（Neo4j）→ コンテキスト圧縮 → 応答

**なぜ簡易実装か？** — 読者が「**GraphRAG と LightRAG の本質的な違い（軽量化、階層化）**」を理解するための最小構成です。

---

## 📋 実験の構成

### グラフ構造

```
Acme Search --[HAS_FEATURE]--> Semantic Index
                              Realtime Query
                              Policy Audit
                              |
                              +--[REGULATES]--> POL-001, POL-002

Globex Graph --[HAS_FEATURE]--> Semantic Index
                                Policy Audit
                                |
                                +--[REGULATES]--> POL-002
```

### ノード

- `Product`: Acme Search, Globex Graph
- `Feature`: Semantic Index, Realtime Query, Policy Audit
- `Policy`: POL-001（Personal Data Protection）, POL-002（AI Model Governance）

### 関係

- `HAS_FEATURE`: 製品が機能を持つ
- `REGULATES`: ポリシーが製品を規制（データに含まれる）

---

## 📊 試験データセット

本実験では、データ量依存性を実証するため、3 つのデータセットサイズを用意しています。

### 8 項目版（デフォルト）

`data/docs-light.jsonl` として提供。8 エントリのテストデータで、以下の内容を含みます：

- 製品と機能の関係
- ポリシーと製品の関係
- 政策変更による影響

### 5 項目版（kg-no-rag と同じ）

`data/docs.jsonl` として提供。`kg-no-rag` 実験と同じデータセットを使用できます。最初の 5 エントリが含まれます。

**特徴**: 小規模データセットで、ベクトル検索の精度の限界を実証します。

### 50 項目版

`data/docs-50.jsonl` として提供。最初の 5 エントリに加え、様々な製品・サービスの説明を追加した 50 エントリのデータセットです。

**特徴**: 同じドメインの情報を様々な表現で繰り返し記述することで、データ量増加に伴うベクトル検索の精度変化を実証します。`kg-no-rag` 実験と同様に、スケール依存性のテストに使用できます。

**データセット切り替え**:

1. **環境変数で指定（推奨）**: `docker-compose.yml` の `environment` セクションで `DATA_FILE` を指定します。

```bash
# docker-compose.yml の environment に以下を追加:
DATA_FILE: data/docs.jsonl        # 5項目版
DATA_FILE: data/docs-light.jsonl  # 8項目版（デフォルト）
DATA_FILE: data/docs-50.jsonl     # 50項目版
```

2. **スクリプトで切り替え**: `switch-dataset.sh` を使用して簡単に切り替えできます（後述）。

3. **動的切り替え**: 実行中に `/switch-dataset` エンドポイントで切り替えることも可能です。

データセットは GraphRAG と LightRAG の両方で共通使用されます。

---

## ❓ テスト質問

実装を手元で実行して、GraphRAG と LightRAG の動作を確認できます。

| ID                     | 質問                                | 期待値                                       | 比較ポイント       |
| ---------------------- | ----------------------------------- | -------------------------------------------- | ------------------ |
| **Q1-製品一覧**        | 製品一覧                            | Acme Search, Globex Graph                    | 基本動作の確認     |
| **Q2-Acme の機能**     | Acme が提供する全ユニークな機能は？ | Realtime Query, Semantic Index               | 集合演算の確認     |
| **Q3-関連ポリシー**    | Globex Graph を規制するポリシーは？ | POL-002                                      | グラフ経路の確認   |
| **Q4-Acme の機能詳細** | Acme の機能は？                     | Semantic Index, Realtime Query, Policy Audit | 多ホップ推論の確認 |
| **Q5-共通機能**        | Acme と Globex の共通機能は？       | Semantic Index                               | 交差演算の確認     |

**注記**: 評価のゆらぎ（バリエーション）を減らすため、質問数を 5 問に拡張しました。`kg-no-rag` 実験と同じデータセット（5 項目版）と質問で比較可能です。

**自動評価**: `/eval` エンドポイントで全質問を一括実行できます（後述）。

---

## 🏗 コンテナ構成

| サービス名     | 役割                             | 補足                                                        |
| -------------- | -------------------------------- | ----------------------------------------------------------- |
| `graphrag-api` | GraphRAG パイプライン（FastAPI） | グラフ探索ベースの検索 API                                  |
| `lightrag-api` | LightRAG パイプライン（FastAPI） | 階層的検索とフィードバック機能を搭載                        |
| `qdrant`       | ベクトル検索層（低レベル）       | GraphRAG / LightRAG 共通で利用                              |
| `neo4j`        | 構造化知識の保管（高レベル）     | グラフ構造を保持し、LightRAG で `w_struct`, `w_attn` を管理 |

### 処理フロー

```
質問 --(embedding)--> Qdrant --(top-k)--> Neo4j 局所グラフ構築 --(score統合)--> コンテキスト圧縮 --(LLM擬似)--> 応答
                                                                                   ↘ attention 出力 → Neo4j エッジ重み更新
```

---

## 🚀 クイックスタート

### 前提

- macOS（または Linux/WSL2）
- Docker / Docker Compose v2
- `curl` コマンド
- `jq` コマンド（オプション、JSON の整形用）

### 実行

```bash
cd experiments/graphrag-lightrag

# 初回ビルドと起動
docker compose up --build -d

# サービス起動状況を確認
docker compose ps
```

> ⏳ **重要**: コンテナ起動後、データベース初期化と埋め込みモデルのダウンロードに **約 60-90 秒** かかります。特に LightRAG は `sentence-transformers/all-MiniLM-L6-v2`（約 80MB）のダウンロードが必要です。初期化が完了していないまま評価を実行するとエラーが発生します。

```bash
# 初期化完了後、自動評価実行
sleep 60
curl -s http://localhost:8100/eval | jq '.'
```

**期待される結果**:

```json
{
  "summary": {
    "graphrag_ok": 3,
    "lightrag_ok": 4,
    "total": 5
  },
  "cases": [
    {
      "id": "Q1-製品一覧",
      "ask": "製品一覧",
      "expected": ["Acme Search", "Globex Graph"],
      "graphrag_nodes": ["Acme Search", "Globex Graph"],
      "lightrag_nodes": ["Acme Search", "Globex Graph"],
      "gr_ok": true,
      "lr_ok": true
    },
    {
      "id": "Q2-Acmeの機能",
      "ask": "Acme が提供する全ユニークな機能は？",
      "expected": ["Realtime Query", "Semantic Index"],
      "graphrag_nodes": ["Realtime Query", "Semantic Index", ...],
      "lightrag_nodes": ["Realtime Query", "Semantic Index", ...],
      "gr_ok": true,
      "lr_ok": true
    }
    ...
  ]
}
```

**注記**: 実際の実行結果は実装の簡易性により変動する可能性があります。評価のゆらぎを減らすため、質問数を 5 問に拡張しました。

### 個別の質問で比較

特定の質問で GraphRAG と LightRAG を比較する場合：

```bash
# 比較実行
curl "http://localhost:8100/compare?question=製品一覧" | jq
```

### 評価スクリプト（便利ツール）

`evaluate.sh` スクリプトを使用すると、簡単に比較評価ができます：

```bash
# ヘルスチェック
./evaluate.sh health

# 特定の質問で比較
./evaluate.sh compare "製品一覧"

# 自動評価実行
./evaluate.sh eval
```

---

## 📝 テスト質問詳細

> **注記**: 以下の結果は、この実装の手元での実行結果を参考として示しています。実装は簡易版のため、完全な GraphRAG / LightRAG とは異なる場合があります。**あなたの環境での実行結果が異なる場合は、それも正常です**。上記のセクション「クイックスタート」で実装を実行して、実際の動作を確認することをお勧めします。

### Q1-製品一覧: 製品一覧

- **期待値**: `["Acme Search", "Globex Graph"]`
- **比較ポイント**: 基本動作の確認
- **GraphRAG**: キーワードベースの簡易検索で製品を返す
- **LightRAG**: ベクトル検索 → グラフ探索の二層検索で製品を返す
- **違い**: LightRAG は `vector_nodes` と `graph_nodes` を分けて返す（階層的検索の証拠）

### Q2-関連ポリシー: 関連ポリシー

- **期待値**: `["POL-001", "POL-002"]`
- **比較ポイント**: グラフ探索の確認
- **GraphRAG**: ポリシーノードをキーワード検索で取得
- **LightRAG**: ベクトル検索で関連文書を取得し、その中からポリシーを抽出
- **違い**: LightRAG は多段階の推論（文書 → ポリシー）を実行

### Q3-Acme の機能: Acme の機能は？

- **期待値**: `["Semantic Index", "Realtime Query", "Policy Audit"]`
- **比較ポイント**: 多ホップ推論の確認
- **GraphRAG**: キーワード検索で直接機能を取得
- **LightRAG**: ベクトル検索で Acme Search を取得 → グラフ探索で関連機能を取得
- **違い**: LightRAG は局所サブグラフを構築して関連機能を見つける

---

## 🔧 API エンドポイント

### `/ask` (GraphRAG)

GraphRAG パイプラインで質問に答えます。

```bash
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}}'
```

### `/ask` (LightRAG)

LightRAG パイプラインで質問に答えます。

```bash
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "top_k": 4, "depth": 2, "theta": 0.3}'
```

### `/compare?question=<質問>`

同一質問で GraphRAG と LightRAG を同時実行し、結果を比較します。

```bash
curl "http://localhost:8100/compare?question=製品一覧" | jq
```

### `/eval`

すべてのテスト質問について GraphRAG と LightRAG の精度を比較します。

```bash
curl "http://localhost:8100/eval" | jq '.'
```

### `/healthz`

ランタイム状態とデータベース接続状況を確認します。

```bash
curl http://localhost:8200/healthz  # GraphRAG
curl http://localhost:8100/healthz  # LightRAG
```

### `/reset`

データを再シードします。

```bash
curl -X POST http://localhost:8200/reset  # GraphRAG
curl -X POST http://localhost:8100/reset  # LightRAG
```

---

## 📊 評価スクリプト

`evaluate.sh` スクリプトを使用すると、簡単に比較評価ができます。

### 使い方

```bash
# ヘルスチェック（両APIの状態確認）
./evaluate.sh health

# 特定の質問で GraphRAG と LightRAG を比較
./evaluate.sh compare "製品一覧は？"

# questions.json に定義されたテスト質問を自動評価
./evaluate.sh eval
```

### コマンド詳細

#### `health` - ヘルスチェック

両 API の接続状況を確認します：

```bash
./evaluate.sh health
```

- GraphRAG API の接続状況（Neo4j, Qdrant）
- LightRAG API の接続状況（Neo4j, Qdrant, 埋め込みモデル）
- Neo4j ブラウザと Qdrant の URL

#### `compare` - 直接比較

同じ質問を GraphRAG と LightRAG に投げて結果を比較します：

```bash
./evaluate.sh compare "政策変更後に中心性が高いプロダクトは？"
```

レスポンスには以下の情報が含まれます：

- GraphRAG の結果
- LightRAG の結果
- ノード数の差分など

#### `eval` - 自動評価

`lightrag/questions.json` に定義された全質問を自動実行し、期待値との一致度を評価します：

```bash
./evaluate.sh eval
```

サマリーには以下が含まれます：

- GraphRAG の正解数/総質問数
- LightRAG の正解数/総質問数
- 各質問の詳細結果

---

---

## 📝 テスト質問詳細

> **注記**: 以下の結果は、この実装の手元での実行結果を参考として示しています。実装は簡易版のため、完全な GraphRAG / LightRAG とは異なる場合があります。**あなたの環境での実行結果が異なる場合は、それも正常です**。上記のセクション「クイックスタート」で実装を実行して、実際の動作を確認することをお勧めします。

### Q1-製品一覧: 製品一覧

- **期待値**: `["Acme Search", "Globex Graph"]`
- **比較ポイント**: 基本動作の確認
- **GraphRAG**: キーワードベースの簡易検索で製品を返す
- **LightRAG**: ベクトル検索 → グラフ探索の二層検索で製品を返す
- **違い**: LightRAG は `vector_nodes` と `graph_nodes` を分けて返す（階層的検索の証拠）

### Q2-関連ポリシー: 関連ポリシー

- **期待値**: `["POL-001", "POL-002"]`
- **比較ポイント**: グラフ探索の確認
- **GraphRAG**: ポリシーノードをキーワード検索で取得
- **LightRAG**: ベクトル検索で関連文書を取得し、その中からポリシーを抽出
- **違い**: LightRAG は多段階の推論（文書 → ポリシー）を実行

### Q3-Acme の機能: Acme の機能は？

- **期待値**: `["Semantic Index", "Realtime Query", "Policy Audit"]`
- **比較ポイント**: 多ホップ推論の確認
- **GraphRAG**: キーワード検索で直接機能を取得
- **LightRAG**: ベクトル検索で Acme Search を取得 → グラフ探索で関連機能を取得
- **違い**: LightRAG は局所サブグラフを構築して関連機能を見つける

---

## 📊 比較結果の解釈

### LightRAG の強み（実験で確認できること）

#### 1. 階層的検索（Hierarchical Retrieval）

**実装状況**: ✅ 完全実装済み

レスポンスで確認できる項目:

- `vector_nodes`: ベクトル検索（低レベル、α スコア）で取得したノード
- `graph_nodes`: グラフ探索（高レベル、β スコア）で追加されたノード
- `metadata.alpha_beta_ratio`: "0.6/0.4"（ベクトル/グラフの重み比率）
- `metadata.final_scores`: 各ノードの最終スコア（α × 0.6 + β × 0.4）

**テスト例**:

```bash
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '{vector_nodes, graph_nodes: .graph_nodes, alpha_beta_ratio: .metadata.alpha_beta_ratio, final_scores: .metadata.final_scores}'
```

**期待される結果**:

- `vector_nodes` と `graph_nodes` が異なる（階層的検索の証拠）
- `final_scores` が各ノードに表示され、重み統合が機能している

---

#### 2. 軽量化（Lightweight）

**実装状況**: ✅ GraphRAG/LightRAG 両方で確認可能

**GraphRAG**: `graph_walk` パラメータで探索範囲を制御

- `metadata.max_depth`: 設定した最大深さ
- `metadata.nodes_explored`: 実際に探索したノード数
- `metadata.actual_depth`: 実際に到達した深さ

**LightRAG**: 局所サブグラフのみを構築

- `metadata.subgraph.total_nodes`: サブグラフ内のノード数
- `metadata.subgraph.depth`: 構築したサブグラフの深さ

**テスト例**:

```bash
# GraphRAG: max_depth=1 vs max_depth=3 の比較
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "graph_walk": {"max_depth": 1, "prune_threshold": 0.2}}' \
  | jq '.metadata | {max_depth, nodes_explored, actual_depth}'

curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}}' \
  | jq '.metadata | {max_depth, nodes_explored, actual_depth}'
```

**期待される結果**:

- `max_depth=3` の方が `nodes_explored` が多くなる（広範囲探索の証拠）
- LightRAG の `subgraph.total_nodes` が GraphRAG の `nodes_explored` より少ない（軽量化の証拠）

---

#### 3. 適応（Adaptive Feedback）

**実装状況**: ✅ 完全実装済み

**機能**:

- `/feedback` エンドポイントで Neo4j のエッジ `w_attn`（attention 重み）を更新
- 更新された `w_attn` は次回のグラフ探索で使用され、スコア計算に反映される

**テスト例**:

```bash
# 1. フィードバック前の結果を確認
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '.metadata.final_scores'

# 2. フィードバックを送信（Semantic Index の重みを増やす）
curl -X POST "http://localhost:8100/feedback" \
  -H "Content-Type: application/json" \
  -d '{"node_id": "Semantic Index", "weight": 0.8}' \
  | jq '{status, updated_edges}'

# 3. フィードバック後の結果を確認（スコアが変化する）
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '.metadata.final_scores'
```

**期待される結果**:

- `updated_edges` が返される（エッジ更新の証拠）
- フィードバック後の `final_scores` が変化する（適応の証拠）

---

#### 4. パラメータ調整

**LightRAG**: `top_k`, `depth`, `theta` を調整することで、検索範囲と精度のバランスを制御可能

**GraphRAG**: `graph_walk.max_depth`, `graph_walk.prune_threshold` を調整することで、探索範囲を制御可能

---

### GraphRAG の特徴（簡易実装での制約）

- 現実装は簡易版（キーワードベース）のため、完全な GraphRAG の特徴（深いグラフ探索、事前分析）は限定的です
- ただし、`graph_walk` パラメータ（`max_depth`, `prune_threshold`）による探索制御は実装済みで、探索ノード数と深さを確認できます

---

## 🧪 詳細なテストシナリオ

LightRAG の改良点を確認するために、GraphRAG と同じ質問セットで差分を観測します。

### シナリオ 1: 多ホップ経路の圧縮精度

**質問**: 「政策強化後、Globex Graph に影響する機能は？」

**手順**:

- GraphRAG: `graph_walk.max_depth=3` で `/ask` を呼び出す
- LightRAG: `depth=2` で `/ask` を呼び出す

**判定**: LightRAG は GraphRAG より少ないノード数で同等の回答を返せるか。

```bash
# GraphRAG
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "政策強化後、Globex Graph に影響する機能は？",
    "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}
  }' | jq

# LightRAG
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "政策強化後、Globex Graph に影響する機能は？",
    "top_k": 4,
    "depth": 2,
    "theta": 0.3
  }' | jq
```

**期待される結果**:

- **GraphRAG**: 広範囲のグラフ探索により、多くのノード（10-15 個程度）を取得する可能性
- **LightRAG**: 局所サブグラフ構築により、関連性の高いノードのみ（4-8 個程度）を取得
- **違い**: LightRAG の方が取得ノード数が少なく、かつ重要な情報（Policy Audit, Semantic Index など）を保持していることを確認

---

### 2. 局所グラフの軽量化

**質問**: 「Acme Search に関連する機能は？」

**手順**:

- GraphRAG と LightRAG で同じ質問を実行し、レスポンスのメタデータで取得ノード数を比較

**判定**: LightRAG の局所グラフが GraphRAG より少ないノード数で重要情報を保持できているか。

```bash
# 比較実行
curl "http://localhost:8100/compare?question=Acme Search に関連する機能は？" | jq '.differences'
```

**期待される結果**:

- **GraphRAG**: 全体グラフから関連ノードを探索（5-10 個程度のノード）
- **LightRAG**: クエリ依存サブグラフのみを構築（3-6 個程度のノード）
- **違い**: `differences.node_count` で LightRAG の方が少ないノード数であることを確認。かつ、重要な機能（Semantic Index, Realtime Query, Policy Audit）が含まれていることを確認

---

### 3. フィードバックループ

**質問**: 「Globex Graph の機能は？」（同じ質問を 3 回繰り返す）

**手順**:

1. LightRAG で同じ質問を 3 回実行
2. 各実行後に `GET /feedback-log` で attention 重みの変化を確認

**判定**: LightRAG で `w_attn` が更新され、回答が安定化していくか。

```bash
# 同じ質問を3回実行
for i in {1..3}; do
  echo "=== 実行 $i ==="
  curl -X POST "http://localhost:8100/ask" \
    -H "Content-Type: application/json" \
    -d '{"question": "Globex Graph の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' | jq '.answer'
  sleep 1
done

# フィードバックログを確認
curl http://localhost:8100/feedback-log | jq
```

**期待される結果**:

- **実行 1 回目**: 初期状態での回答（Semantic Index, Policy Audit など）
- **実行 2-3 回目**: フィードバックによる重み更新の影響（回答の安定化や関連ノードの優先度変化）
- **フィードバックログ**: `feedback-log` に更新履歴が記録される（実験環境では手動フィードバックを `/feedback` で投入する必要があります）

> **注記**: 実験環境は簡易実装のため、LLM からの自動的な attention 重み取得は実装されていません。完全な動作については[LightRAG 公式リポジトリ](https://github.com/HKUDS/LightRAG)を参照してください。

---

### 4. スループット（任意）

**手順**: それぞれ `/ask` を複数回呼び出して平均レスポンスタイムを測定

**期待される結果**:

- **GraphRAG**: 全体グラフ探索のため、レスポンスタイムが比較的長い（200-500ms 程度）
- **LightRAG**: 局所サブグラフ構築のため、レスポンスタイムが比較的短い（100-300ms 程度）
- **違い**: LightRAG の方が平均レスポンスタイムが短いことを確認（実測値はデータセットサイズやネットワーク環境により変動）

```bash
# GraphRAG のベンチマーク
time for i in {1..5}; do
  curl -s -X POST "http://localhost:8200/ask" \
    -H "Content-Type: application/json" \
    -d '{"question": "製品一覧を教えて", "graph_walk": {"max_depth": 2}}' > /dev/null
done

# LightRAG のベンチマーク
time for i in {1..5}; do
  curl -s -X POST "http://localhost:8100/ask" \
    -H "Content-Type: application/json" \
    -d '{"question": "製品一覧を教えて", "top_k": 4, "depth": 2, "theta": 0.3}' > /dev/null
done
```

---

## 📂 ディレクトリ構造

```
experiments/graphrag-lightrag/
├── README.md                 # このファイル
├── docker-compose.yml        # コンテナ定義（GraphRAG & LightRAG 両対応）
├── data/                     # 共通データセット
│   └── docs-light.jsonl      # GraphRAG / LightRAG 共通のデータセット（8エントリ）
├── graphrag/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py               # FastAPI: /ask, /reset, /connections など
│   ├── pipeline.py           # GraphRAG パイプライン実装
│   └── data/
│       └── docs-light.jsonl  # → ../../data/docs-light.jsonl へのシンボリックリンク
├── lightrag/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py               # FastAPI: /ask, /compare, /eval, /feedback, /reset など
│   ├── pipeline.py           # LightRAG パイプライン実装
│   ├── questions.json        # 自動評価用のテスト質問セット
│   └── data/
│       └── docs-light.jsonl  # → ../../data/docs-light.jsonl へのシンボリックリンク
└── [データボリューム]
```

データセット (`data/docs-light.jsonl`) は GraphRAG / LightRAG 共通で使用し、記事のケーススタディ（政策変更・フィードバックループなど）をそのまま埋め込みます。`graphrag/data/` と `lightrag/data/` の `docs-light.jsonl` は共通ファイルへのシンボリックリンクです。

---

## 🔧 トラブルシューティング

### サービスが起動しない

**症状**: `docker compose ps` でコンテナの状態が `unhealthy` や `Exit`

**確認方法**:

```bash
# ログを確認
docker compose logs graphrag
docker compose logs lightrag
docker compose logs neo4j
docker compose logs qdrant

# コンテナの状態を確認
docker compose ps
```

**対処法**:

1. ポートの競合がないか確認（7474, 7687, 6333, 8200, 8100）
2. 既存のコンテナをクリーンアップ: `docker compose down -v`
3. 再ビルド: `docker compose up --build -d`

---

### データベース接続エラー

**症状**: `/healthz` や `/connections` で `"connected": false` が返る

**Neo4j 接続エラー**:

```bash
# 接続状況を確認
curl http://localhost:8200/connections | jq '.neo4j'
curl http://localhost:8100/connections | jq '.neo4j'

# Neo4jコンテナが正常に起動しているか確認
docker compose logs neo4j | tail -20

# Neo4jが起動するまで待機（最大60秒）
# その後、サービスを再起動
docker compose restart graphrag lightrag
```

**Qdrant 接続エラー**:

```bash
# Qdrantの状態を確認
curl http://localhost:6333/collections

# Qdrantコンテナのログを確認
docker compose logs qdrant | tail -20

# Qdrantコンテナを再起動
docker compose restart qdrant
```

**対処法**:

```bash
# サービスを再起動
docker compose restart graphrag lightrag

# それでも解決しない場合、クリーンアップして再起動
docker compose down -v
docker compose up --build -d
sleep 60  # 初期化待機
```

---

### 埋め込みモデルのダウンロードが遅い/失敗

**症状**: LightRAG のログに `⚠ Embedding model loading failed` が表示される

**確認方法**:

```bash
# LightRAGのログを確認
docker compose logs lightrag | grep -i "embedding\|model"

# 初回起動時は約80MBのダウンロードが必要（数分かかる場合あり）
docker compose logs -f lightrag
```

**対処法**:

1. ネットワーク接続を確認
2. ダウンロード完了まで待機（初回のみ数分かかる）
3. 失敗している場合、コンテナを再起動:
   ```bash
   docker compose restart lightrag
   docker compose logs -f lightrag
   ```

---

### `/compare` や `/eval` エンドポイントでエラー

**症状**: `GraphRAG request failed` などのエラーが返る

**原因**:

- GraphRAG API が起動していない
- GraphRAG API へのネットワーク接続が失敗している

**確認方法**:

```bash
# GraphRAG APIのヘルスチェック
curl http://localhost:8200/healthz

# 接続状況の確認
curl http://localhost:8200/connections
```

**対処法**:

1. GraphRAG API が起動しているか確認: `docker compose ps graphrag`
2. GraphRAG API を再起動: `docker compose restart graphrag`
3. 60 秒待機してから再試行

---

### 初期化が完了していないまま API を呼び出した

**症状**: `503 Service Unavailable` や `Database connections not ready` エラー

**対処法**:

```bash
# 初期化完了まで待機
sleep 60

# または、ヘルスチェックで確認
while ! curl -sf http://localhost:8200/healthz > /dev/null; do
  echo "Waiting for GraphRAG API..."
  sleep 5
done

while ! curl -sf http://localhost:8100/healthz > /dev/null; do
  echo "Waiting for LightRAG API..."
  sleep 5
done

echo "All services are ready!"
```

---

### データが表示されない/空の結果が返る

**症状**: `/ask` で `No answer generated` や空のノードリストが返る

**原因**: データのシードが完了していない可能性

**対処法**:

```bash
# データを再シード
curl -X POST http://localhost:8200/reset
curl -X POST http://localhost:8100/reset

# シード完了を確認（ログに "✓ Data seeding: success" が表示される）
docker compose logs graphrag | grep "Data seeding"
docker compose logs lightrag | grep "Data seeding"
```

---

## 📌 実装上の注意点

- **GraphRAG 実装**: 現在は簡易実装（キーワードベース）。Microsoft GraphRAG CLI 統合は未対応
- **LightRAG 実装**: 簡易実装だが、埋め込みモデルと Qdrant 検索は動作中
- **データセット**: `docs-light.jsonl` は 8 エントリのテストデータ。拡張可能
- **依存関係**: `requirements.txt` 変更時は `docker compose build --no-cache` が必要

---

## 📝 内部向け: 試験結果と考察メモ

### 試験結果（2025-10-30 時点）

全パターン（5 項目・8 項目・50 項目）での評価結果：

| データセット  | GraphRAG | LightRAG | 考察                                          |
| ------------- | -------- | -------- | --------------------------------------------- |
| **5 項目版**  | 4/5      | 4/5      | 同等。ベクトル検索が有効に機能                |
| **8 項目版**  | 4/5      | **5/5**  | LightRAG 優位。階層的検索が最適に動作         |
| **50 項目版** | **4/5**  | 3/5      | GraphRAG 優位。ベクトル検索のノイズ増加が影響 |

### 主要な考察

1. **GraphRAG の特性**:

   - データ量に依存せず、精度が安定（全パターンで 4/5 を維持）
   - グラフ構造探索ベースのため、ベクトル検索のノイズの影響を受けない

2. **LightRAG の特性**:

   - **効率性・運用性**: 明確に優れている（計算量削減、更新コスト低減）
   - **精度**: データ量に依存する
     - 小規模・中規模（5-8 項目）: GraphRAG と同等または優れる
     - 大規模（50 項目）: ベクトル検索層のノイズ増加により精度が低下

3. **LightRAG の二層構造の意義**:

   - 低レベル（ベクトル検索）: 高速で意味的類似性を捉えるが、データ量に依存しやすい
   - 高レベル（グラフ探索）: ベクトル検索の結果を補完・拡張
   - データ量が増えると、最初のベクトル検索段階でノイズが増え、後のグラフ探索にも影響

4. **kg-no-rag 実験との整合性**:

   - 通常の RAG（ベクトル検索のみ）: データ量増加で精度低下（5 項目: 2/5 → 50 項目: 1/5）
   - LightRAG もベクトル検索層を持つため、同様の傾向（ただし軽減されている）
   - GraphRAG はグラフ探索のみのため、データ量の影響を受けにくい

5. **「LightRAG は効率性重視で精度が劣る」という理解は不正確**:

   - 精度はデータ量に依存する（常に劣るわけではない）
   - 中規模データでは LightRAG が優れる場合がある
   - 大規模データでは、ベクトル検索の制約により精度が低下する傾向

6. **ハイブリッドアプローチ（GraphRAG→LightRAG）について**:
   - 技術的には可能だが、LightRAG の設計思想と矛盾する
   - ベクトル検索の利点（意味的類似性）が失われる
   - 二重グラフ探索となり、軽量化の意義が薄れる
   - **結論**: 実装する必要性は低い。現在の GraphRAG vs LightRAG の対比が適切

### 記事との整合性確認

- **記事の主張**: LightRAG は「効率性・運用性」の改善を主眼としている
- **精度について**: 記事では明示的に「精度で優れる」とは書かれていない
- **試験結果**: 記事の主張と整合。効率性は優れ、精度はデータ量に依存する

---

## 📚 関連リンク

- 記事: [GraphRAG の限界と LightRAG の登場](../articles/graphrag-light-rag-2025-10.md)
- Microsoft GraphRAG: [GitHub](https://github.com/microsoft/graphrag)
- HKUDS LightRAG: [GitHub](https://github.com/HKUDS/LightRAG)

## 📖 記事に沿ったテストガイド

記事を読みながら、実際に動作確認できる比較ポイントをまとめたテストガイドを用意しています：

**→ [TESTING_GUIDE.md](./TESTING_GUIDE.md)**

このガイドでは、記事の各章に対応したテスト方法を説明しています：

- 軽量化（Lightweight）の実証
- 階層化（Hierarchical Retrieval）の二層検索の確認
- 適応（Adaptive Feedback）の動作確認
- GraphRAG との定量的比較

記事を読み進めながら、このガイドに沿って実際に API を呼び出すことで、理論と実装の違いを体感できます。

---

## 💡 よくある質問

### GraphRAG と LightRAG の違いを一目で確認したい場合は？

`/compare` エンドポイントを使用して、同じ質問で両方を同時に実行し、結果を比較できます：

```bash
curl "http://localhost:8100/compare?question=製品一覧は？" | jq
```

レスポンスには GraphRAG と LightRAG の両方の結果と、ノード数の差分などが含まれます。

### 自動で複数の質問をテストしたい場合は？

`/eval` エンドポイントを使用して、`questions.json` に定義されたテスト質問を自動実行できます：

```bash
curl http://localhost:8100/eval | jq
```

各質問について GraphRAG と LightRAG の結果を比較し、期待値との一致度をサマリーで返します。

### データセットを変更したい場合は？

#### 方法 1: スクリプトで切り替え（推奨）

`switch-dataset.sh` スクリプトを使用すると、簡単にデータセットを切り替えてテストできます：

```bash
# 小規模版（5個）でテスト
./switch-dataset.sh small

# 中規模版（8個）でテスト
./switch-dataset.sh medium

# 大規模版（50個）でテスト
./switch-dataset.sh large

# 小規模と大規模を比較
./switch-dataset.sh compare
```

スクリプトは自動的にコンテナを再起動し、初期化完了後に評価を実行します。

#### 方法 2: 環境変数で切り替え

`docker-compose.yml` の environment セクションに `DATA_FILE` を追加してください。

```bash
# docker-compose.yml を編集
# graphrag と lightrag の environment に以下を追加:
#   DATA_FILE: data/docs.jsonl        # 5項目版を使用（kg-no-ragと同じ）
#   DATA_FILE: data/docs-light.jsonl  # 8項目版を使用（デフォルト）
#   DATA_FILE: data/docs-50.jsonl     # 50項目版を使用

# 再ビルドと再起動
docker compose down -v
docker compose up --build -d
sleep 60
```

#### 方法 3: 動的切り替え（実行中）

コンテナが起動している状態で、`/switch-dataset` エンドポイントを使用して切り替えることも可能です：

```bash
# GraphRAG のデータセットを切り替え
curl -X POST "http://localhost:8200/switch-dataset?file=data/docs-50.jsonl" | jq

# LightRAG のデータセットを切り替え
curl -X POST "http://localhost:8100/switch-dataset?file=data/docs-50.jsonl" | jq
```

現在のデータセット情報を確認するには：

```bash
curl http://localhost:8200/dataset | jq
curl http://localhost:8100/dataset | jq
```

**注意**: 動的切り替え後は、`/reset` を呼び出すと環境変数のデフォルト値に戻るため、恒久的に変更したい場合は環境変数での設定を推奨します。

### データ量依存性のテストはどのように行う？

`kg-no-rag` 実験と同様に、データ量による精度変化を実証できます：

1. **小規模（5 個）と大規模（50 個）の比較**: `./switch-dataset.sh compare` を実行すると、自動的に両方をテストして結果を比較表示します。

2. **手動での比較**: 以下の手順で実行することも可能です：

```bash
# 小規模版のテスト
./switch-dataset.sh small

# 結果を確認・記録（例: GraphRAG: 5/5, LightRAG: 3/5）

# 大規模版のテスト
./switch-dataset.sh large

# 結果を確認・記録（例: GraphRAG: 5/5, LightRAG: 2/5）
```

**期待される動作**:

- GraphRAG: データ量に依存せず、グラフ構造に基づく検索のため安定した精度を維持
- LightRAG: データ量が増えると、ベクトル検索段階でノイズが増え、精度が低下する可能性がある（簡易実装の制約による）

これは `kg-no-rag` 実験で実証される「RAG はデータ量に依存するが、KG は依存しない」という仮説の検証に使用できます。

#### 方法 4: ファイルを直接編集

`data/docs-light.jsonl` を編集してください。このファイルは GraphRAG と LightRAG の両方で共有されています。

```bash
# エディタで編集
vim data/docs-light.jsonl

# データを再シード
curl -X POST http://localhost:8200/reset  # GraphRAG
curl -X POST http://localhost:8100/reset  # LightRAG
```

#### kg-no-rag と同じデータセットで試す

`kg-no-rag` 実験と同じ 5 項目データセットを使用する場合：

```bash
# 環境変数を設定して起動（推奨）
# docker-compose.yml の graphrag と lightrag の environment に以下を追加:
#   DATA_FILE: data/docs.jsonl

# または、シンボリックリンクを作成
cd experiments/graphrag-lightrag
ln -sf docs.jsonl data/docs-light.jsonl

# データを再シード
curl -X POST http://localhost:8200/reset  # GraphRAG
curl -X POST http://localhost:8100/reset  # LightRAG
```

### 特定の質問パターンで比較したい場合は？

`lightrag/questions.json` を編集して、テスト質問を追加・変更できます。JSON 形式で以下の構造です：

```json
[
  {
    "id": "Q1-製品一覧",
    "ask": "製品一覧",
    "expected": ["Acme Search", "Globex Graph"]
  }
]
```

編集後、`/eval` エンドポイントで新しい質問セットが使用されます。

### Neo4j のブラウザで手動確認したい場合は？

`http://localhost:7474` にアクセスしてください。認証情報は `neo4j` / `password` です。

ブラウザ上で Cypher クエリを実行して、グラフ構造を直接確認できます：

```cypher
MATCH (n) RETURN n LIMIT 50
```

### Qdrant の状態を確認したい場合は？

`http://localhost:6333/dashboard` にアクセスすると、Qdrant のダッシュボードが表示されます（Qdrant のバージョンによる）。

または、API で確認できます：

```bash
curl http://localhost:6333/collections | jq
```

---

## 📝 ライセンス

この実験環境は記事の読者向けに提供されています。各ライブラリのライセンスについては、それぞれのリポジトリを参照してください。
