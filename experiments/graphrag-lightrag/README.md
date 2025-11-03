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

## 📊 データセット

本実験では、データ量依存性を実証するため、複数のデータセットサイズを用意しています。

| データセット           | ファイル名         | ノード数（推定） | 説明                               |
| ---------------------- | ------------------ | ---------------- | ---------------------------------- |
| 5 項目版               | `docs.jsonl`       | ~7 ノード        | `kg-no-rag` 実験と同じデータセット |
| 8 項目版（デフォルト） | `docs-light.jsonl` | ~8 ノード        | テストデータ                       |
| 50 ノード版            | `docs-50.jsonl`    | ~50 ノード       | 中規模データセット                 |
| 300 ノード版           | `docs-300.jsonl`   | ~300 ノード      | 大規模データセット（平均次数 4）   |
| 500 ノード版           | `docs-500.jsonl`   | ~500 ノード      | 超大規模データセット（平均次数 4） |
| 1000 ノード版          | `docs-1000.jsonl`  | ~1000 ノード     | 最大規模データセット（平均次数 5） |

**注意**: ノード数はエンティティ抽出によって自動的に決定されます。新しいエンティティ抽出ロジックにより、製品名・機能名・ポリシー名が自動的に検出されます。

**データセット切り替え**: `switch-dataset.sh` を使用（コンテナ再起動なし）

```bash
./switch-dataset.sh small     # 5項目版（~7ノード）
./switch-dataset.sh medium    # 8項目版（~8ノード）
./switch-dataset.sh size50    # 50ノード版
./switch-dataset.sh size300   # 300ノード版
./switch-dataset.sh size500   # 500ノード版
./switch-dataset.sh size1000  # 1000ノード版
```

**データセット生成**: 新しいデータセットを生成する場合は `generate-dataset.py` を使用します。

```bash
python3 generate-dataset.py --size 300 --degree 4 --output data/docs-300.jsonl
python3 generate-dataset.py --size 500 --degree 4 --output data/docs-500.jsonl
python3 generate-dataset.py --size 1000 --degree 5 --output data/docs-1000.jsonl
```

---

## ❓ テスト質問

**重要**: この質問セットは `kg-no-rag` 実験と同じ内容です。これにより、**KG（ナレッジグラフ）、RAG（ベクトル検索）、GraphRAG、LightRAG** の 4 つの手法を同じ質問で比較できます。

| ID          | 型   | 質問                                                                   | 期待値                         |
| ----------- | ---- | ---------------------------------------------------------------------- | ------------------------------ |
| **Q1-集合** | 集合 | Acme が提供する全ユニークな機能は？                                    | Realtime Query, Semantic Index |
| **Q2-差分** | 対比 | Semantic Index を提供する製品で、Policy Audit を提供していない製品は？ | Acme Search                    |
| **Q3-経路** | 経路 | Globex Graph を規制するポリシーは？                                    | POL-002                        |
| **Q4-否定** | 否定 | Semantic Index を持たない機能は？                                      | Policy Audit, Realtime Query   |
| **Q5-交差** | 交差 | Acme と Globex の共通機能は？                                          | Semantic Index                 |

---

## 🏗 コンテナ構成

| サービス名     | 役割                             |
| -------------- | -------------------------------- |
| `graphrag-api` | GraphRAG パイプライン（FastAPI） |
| `lightrag-api` | LightRAG パイプライン（FastAPI） |
| `qdrant`       | ベクトル検索層（低レベル）       |
| `neo4j`        | 構造化知識の保管（高レベル）     |

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

# 初期化完了まで待機（約 60-90 秒）
sleep 90

# ヘルスチェック
curl -sf http://localhost:8200/healthz  # GraphRAG
curl -sf http://localhost:8100/healthz  # LightRAG
```

### 違いをすぐに確認する

**1. 精度比較（全質問を一括実行）**

```bash
curl -s http://localhost:8100/eval | jq '.summary'
```

**2. 同じ質問で探索プロセスを比較**

```bash
curl -G "http://localhost:8100/compare" --data-urlencode "question=Acme Search の機能は？" | jq '.'
```

**3. 階層的検索を確認（LightRAG の特徴）**

```bash
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '{vector_nodes, graph_nodes: .graph_nodes, subgraph}'
```

---

## 📈 データセットを段階的に大きくする

小規模データセットで動作確認できたら、データセットを大きくして **LightRAG の軽量化の効果** を確認しましょう。データセットサイズが大きくなるほど、探索ノード数の差が明確になります。

### 手順

**1. データセットを切り替え**

```bash
# 50ノード版に切り替え（中規模）
./switch-dataset.sh size50

# 切り替え完了まで待機（約 30-60 秒）
sleep 60

# ヘルスチェックで確認
curl -sf http://localhost:8200/healthz
curl -sf http://localhost:8100/healthz
```

**2. 軽量化の効果を確認**

```bash
# GraphRAG: 探索ノード数を確認
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "graph_walk": {"max_depth": 5, "prune_threshold": 0.0}}' \
  | jq '.metadata.nodes_explored'

# LightRAG: サブグラフのノード数を確認
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '.subgraph.total_nodes'
```

**3. さらに大きなデータセットに切り替え**

```bash
# 300ノード版に切り替え（大規模）
./switch-dataset.sh size300
sleep 60

# 探索ノード数を再確認（差がより明確になる）
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "graph_walk": {"max_depth": 5, "prune_threshold": 0.0}}' \
  | jq '.metadata.nodes_explored'

curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '.subgraph.total_nodes'
```

**4. 最大規模のデータセット（オプション）**

```bash
# 500ノード版
./switch-dataset.sh size500
sleep 60

# 1000ノード版
./switch-dataset.sh size1000
sleep 60

# 各サイズで探索ノード数を比較
```

### 期待される結果

各データセットサイズでの探索ノード数の目安は、以下の「軽量化（Lightweight）」セクションを参照してください。データセットが大きくなるほど、LightRAG の局所サブグラフ構築による探索コスト削減の効果が明確になります。

**注意**:

- データセット切り替え後、初期化完了まで約 30-60 秒かかります
- 大規模データセットでは初期化に 1-2 分かかる場合があります
- ヘルスチェックで確認してから実験を続けてください

---

## 📊 GraphRAG vs LightRAG の違いを確認する方法

### 1. 階層的検索（Hierarchical Retrieval）

LightRAG はベクトル検索（低レベル）とグラフ探索（高レベル）の二層検索を行います。

**確認方法**:

```bash
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '{vector_nodes, graph_nodes: .graph_nodes, alpha_beta_ratio: .metadata.alpha_beta_ratio}'
```

**確認ポイント**:

- `vector_nodes`: ベクトル検索で取得したノード
- `graph_nodes`: グラフ探索で追加されたノード
- `alpha_beta_ratio`: ベクトル/グラフの重み比率（例: "0.6/0.4"）

### 2. 軽量化（Lightweight）

LightRAG はクエリ依存の局所サブグラフのみを構築します。`top_k`パラメータで探索範囲を制御できるため、必要な情報だけを取得できます。

**確認方法**:

```bash
# GraphRAG: 広範囲探索（max_depthを大きくして多くのノードを探索）
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "graph_walk": {"max_depth": 5, "prune_threshold": 0.0}}' \
  | jq '.metadata.nodes_explored'

# LightRAG: 局所サブグラフ（top_kを小さくして探索範囲を制限）
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 2, "depth": 1, "theta": 0.3}' \
  | jq '.subgraph.total_nodes'
```

**期待される違い**:

- GraphRAG: パラメータ調整で探索範囲を広げられるが、関連ノードを広く探索する傾向がある
- LightRAG: `top_k`を小さくすることで局所サブグラフのみを構築し、探索コストを削減できる

**期待される結果（参考・本実装の実測と整合）**:

- **size50**（中規模）:
  - GraphRAG（`max_depth=5`）: 平均 ~5 ノード探索（小規模では範囲が狭い）
  - LightRAG（`top_k=4, depth=2`）: 平均 ~25 ノード（埋め込み・局所サブグラフの初期オーバーヘッド）
- **size300**（大規模）:
  - GraphRAG: 平均 ~283 ノード探索、レイテンシ ~259ms（広範囲探索）
  - LightRAG: 平均 ~27 ノード、レイテンシ ~18ms（局所サブグラフで安定）
- **size500**（超大規模）:
  - GraphRAG: 平均 ~256 ノード、レイテンシ ~266ms
  - LightRAG: 平均 ~30 ノード、レイテンシ ~24ms
- **size1000**（最大規模）:
  - GraphRAG: 平均 ~458 ノード、レイテンシ ~675ms（規模増大で顕著に増加）
  - LightRAG: 平均 ~30 ノード、レイテンシ ~31ms（ほぼ一定）

**注意**: 探索ノード数の差は、データセットサイズが大きくなるほど明確になります。LightRAG の軽量化の価値は、**探索コストの削減**（`top_k`による探索範囲の制限）と**更新の柔軟性**（クエリ毎に局所サブグラフを構築するため全体再構築が不要）にあります。また、**階層的検索**（ベクトル検索とグラフ探索の二層構造）により、より効率的な情報取得が可能です。

### 3. 適応（Adaptive Feedback）

LightRAG はフィードバックによってエッジ重みを動的調整できます。

**確認方法**:

```bash
# フィードバック前
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '.metadata.final_scores'

# フィードバック送信
curl -X POST "http://localhost:8100/feedback" \
  -H "Content-Type: application/json" \
  -d '{"node_id": "Semantic Index", "weight": 0.8}' | jq

# フィードバック後（スコアが変化）
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '.metadata.final_scores'
```

---

## 🎁 おまけ: KG/RAG/GraphRAG/LightRAG の 4 手法比較

`kg-no-rag` 実験と同じデータセット（5 項目版の `docs.jsonl`）と質問セットを使用することで、4 つの手法を同じ条件で比較できます。

### 比較方法

1. **KG（ナレッジグラフ）**: `kg-no-rag` 実験で確認（Cypher クエリ）
2. **RAG（ベクトル検索）**: `kg-no-rag` 実験で確認（Qdrant）
3. **GraphRAG**: この実験で確認（グラフ探索ベース）
4. **LightRAG**: この実験で確認（階層的検索）

**データセット切り替え**:

```bash
# kg-no-ragと同じ5項目版に切り替え
./switch-dataset.sh small

# 評価実行
curl -s http://localhost:8100/eval | jq '.summary'
```

**期待される傾向（この実装の実測に基づく）**:

- **KG**: すべての質問で正確（5/5）✅
- **RAG**: 小規模では一部成功、大規模で精度低下 ❌
- **GraphRAG**: 小規模では良好（4/5）、規模増大で精度低下（1/5→0/5）、探索ノード数・レイテンシが増加 ❌
- **LightRAG**: 小規模では GraphRAG より遅いことがあるが、規模増大後も精度（2/5）・探索ノード（~30）・レイテンシ（~30ms）が安定 ✅

---

## 🔧 API エンドポイント

### `/ask` (GraphRAG)

```bash
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}}'
```

### `/ask` (LightRAG)

```bash
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}'
```

### `/compare`

同じ質問で GraphRAG と LightRAG を比較します。

```bash
curl -G "http://localhost:8100/compare" --data-urlencode "question=Acme Search の機能は？" | jq '.'
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

---

## 📊 評価スクリプト

`evaluate.sh` スクリプトを使用すると、簡単に比較評価ができます：

### 基本的な使い方

```bash
# ヘルスチェック
./evaluate.sh health

# 特定の質問で比較
./evaluate.sh compare "Acme Search の機能は？"

# 自動評価実行（現在のデータセット）
./evaluate.sh eval
```

### データセットを指定して評価

データセットを指定すると、自動的にデータセットを切り替えてから評価を実行します：

```bash
# 小規模版（5個）で評価
./evaluate.sh eval small

# 中規模版（約50ノード）で評価
./evaluate.sh eval size50

# 大規模版（約300ノード）で評価
./evaluate.sh eval size300

# 超大規模版（約500ノード）で評価
./evaluate.sh eval size500

# 最大規模版（約1000ノード）で評価
./evaluate.sh eval size1000
```

### 全データセットで順番に比較評価

複数のデータセットで順番に評価を実行し、結果を比較できます：

```bash
# 全データセットで順番に評価実行
./evaluate.sh eval-all
```

このコマンドは、以下のデータセットで順番に評価を実行し、最後に比較結果のまとめを表示します：

- `small` (小規模版)
- `size50` (中規模版)
- `size300` (大規模版)
- `size500` (超大規模版)
- `size1000` (最大規模版)

---

## 📌 参考値（この環境での実測・2025-11-03）

以下は本リポジトリの実装・同一環境で `/eval` を実行した際の参考値です。

再現コマンド:

```bash
./evaluate.sh eval-all
```

| データセット | 精度 (GraphRAG/LightRAG) | 探索ノード数 平均 (GraphRAG/LightRAG) | レイテンシ 平均 ms (GraphRAG/LightRAG) |
| ------------ | ------------------------ | ------------------------------------- | -------------------------------------- |
| small        | 4/5 / 3/5                | 5.0 / 28.6                            | 12.39 / 50.19                          |
| size50       | 4/5 / 2/5                | 5.2 / 24.8                            | 13.95 / 55.48                          |
| size300      | 1/5 / 2/5                | 283.0 / 26.8                          | 258.71 / 18.25                         |
| size500      | 0/5 / 2/5                | 255.8 / 29.8                          | 266.47 / 23.58                         |
| size1000     | 0/5 / 2/5                | 457.8 / 30.0                          | 675.39 / 31.0                          |

注記:

- 本実験の GraphRAG は学習用の簡易実装であり、大規模データセットでは精度が低下しやすい想定です。
- LightRAG は大規模でも探索ノード数が約 30 で安定し、レイテンシも低く保たれる傾向を確認できました。
- 数値は環境や乱数により前後するため、あくまで目安としてご参照ください。

### データセットサイズ別の傾向（要点）

- 精度の推移:

  - small: GraphRAG (4/5) > LightRAG (3/5)
  - size50: GraphRAG (4/5) > LightRAG (2/5)
  - size300: GraphRAG (1/5) < LightRAG (2/5)
  - size500: GraphRAG (0/5) < LightRAG (2/5)
  - size1000: GraphRAG (0/5) < LightRAG (2/5)

- 探索ノード数の推移（平均）:

  - small: GraphRAG (5.0) < LightRAG (28.6)
  - size50: GraphRAG (5.2) < LightRAG (24.8)
  - size300: GraphRAG (283.0) > LightRAG (26.8) ← 逆転
  - size500: GraphRAG (255.8) > LightRAG (29.8) ← 逆転
  - size1000: GraphRAG (457.8) > LightRAG (30.0) ← 逆転

- レイテンシの推移（平均 ms）:
  - small: GraphRAG (12.39) < LightRAG (50.19)
  - size50: GraphRAG (13.95) < LightRAG (55.48)
  - size300: GraphRAG (258.71) > LightRAG (18.25) ← 逆転
  - size500: GraphRAG (266.47) > LightRAG (23.58) ← 逆転
  - size1000: GraphRAG (675.39) > LightRAG (31.0) ← 逆転

---

## 📊 比較結果の解釈

### 小規模環境での傾向（技術的注意）

この実装は学習用の簡易構成です。実測では次のような傾向が観測されます：

- **精度（/eval）**: 小規模〜中規模データでは GraphRAG と LightRAG が同点になることがある
- **圧縮（LightRAG）**: `top_k` を小さくすると回答長も短くなる（文脈予算を制御可能）
- **探索規模**: GraphRAG の `nodes_explored` と LightRAG の `subgraph.total_nodes` を比較
- **レイテンシ**: 小規模では GraphRAG（簡易実装）の方が速く見える場合がある。LightRAG は埋め込み生成＋ベクトル検索の固定オーバーヘッドがあるため

**重要な前提**:

- 研究版 GraphRAG は「全体グラフ構築・コミュニティ要約」などの重い前処理を伴い、運用・更新コストが増大しやすい
- LightRAG は「クエリ毎の局所サブグラフ＋圧縮＋フィードバック」で、データ増大時も `top_k` と `depth` により計算を局所化しやすい（運用効率）

---

## 💡 よくある質問

**Q: GraphRAG と LightRAG の違いを一目で確認したい場合は？**

A: `/compare` エンドポイントを使用して、同じ質問で両方を同時に実行し、結果を比較できます：

```bash
curl -G "http://localhost:8100/compare" --data-urlencode "question=Acme Search の機能は？" | jq
```

**Q: 自動で複数の質問をテストしたい場合は？**

A: `/eval` エンドポイントを使用して、`questions.json` に定義されたテスト質問を自動実行できます：

```bash
curl http://localhost:8100/eval | jq
```

**Q: データセットを変更したい場合は？**

A: `switch-dataset.sh` スクリプトを使用します（コンテナ再起動なし）：

```bash
./switch-dataset.sh small     # 5項目版（~7ノード）
./switch-dataset.sh medium    # 8項目版（~8ノード）
./switch-dataset.sh size50    # 50ノード版
./switch-dataset.sh size300   # 300ノード版
./switch-dataset.sh size500   # 500ノード版
./switch-dataset.sh size1000  # 1000ノード版
```

**Q: 新しいデータセットを生成したい場合は？**

A: `generate-dataset.py` スクリプトを使用します：

```bash
python3 generate-dataset.py --size 300 --degree 4 --output data/docs-300.jsonl
```

このスクリプトは、指定されたノード数と平均次数を持つデータセットを生成します。エンティティ抽出ロジックにより、製品名・機能名・ポリシー名が自動的に検出されます。

**Q: Neo4j のブラウザで手動確認したい場合は？**

A: `http://localhost:7474` にアクセスしてください。認証情報は `neo4j` / `password` です。

---

## 🔧 トラブルシューティング

**サービスが起動しない**

```bash
# ログを確認
docker compose logs graphrag lightrag neo4j qdrant

# クリーンアップして再起動
docker compose down -v
docker compose up --build -d
sleep 90
```

**初期化が完了していない**

コンテナ起動後、データベース初期化と埋め込みモデルのダウンロードに **約 60-90 秒** かかります。ヘルスチェックで確認してください：

```bash
curl -sf http://localhost:8200/healthz
curl -sf http://localhost:8100/healthz
```

**データが表示されない**

```bash
# データを再シード
curl -X POST http://localhost:8200/reset  # GraphRAG
curl -X POST http://localhost:8100/reset  # LightRAG
```

---

## 📌 実装上の注意点

- **GraphRAG 実装**: 現在は簡易実装（キーワードベース）。Microsoft GraphRAG CLI 統合は未対応
- **LightRAG 実装**: 簡易実装だが、埋め込みモデルと Qdrant 検索は動作中
- **データセット**: `docs-light.jsonl` は 8 エントリのテストデータ。拡張可能
- **依存関係**: `requirements.txt` 変更時は `docker compose build --no-cache` が必要

---

## 📚 関連リンク

- 記事: [GraphRAG の限界と LightRAG の登場](../articles/graphrag-light-rag-2025-10.md)
- Microsoft GraphRAG: [GitHub](https://github.com/microsoft/graphrag)
- HKUDS LightRAG: [GitHub](https://github.com/HKUDS/LightRAG)

---

## 📝 ライセンス

この実験環境は記事の読者向けに提供されています。各ライブラリのライセンスについては、それぞれのリポジトリを参照してください。
