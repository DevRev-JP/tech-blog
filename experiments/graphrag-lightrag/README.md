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

| データセット           | ファイル名         | 説明                               |
| ---------------------- | ------------------ | ---------------------------------- |
| 5 項目版               | `docs.jsonl`       | `kg-no-rag` 実験と同じデータセット |
| 8 項目版（デフォルト） | `docs-light.jsonl` | テストデータ                       |
| 50 項目版              | `docs-50.jsonl`    | 大規模データセット                 |
| 100 項目版             | `docs-100.jsonl`   | 超大規模データセット               |
| 200 項目版             | `docs-200.jsonl`   | 最大規模データセット               |

**データセット切り替え**: `switch-dataset.sh` を使用（コンテナ再起動なし）

```bash
./switch-dataset.sh small    # 5項目版
./switch-dataset.sh medium   # 8項目版（デフォルト）
./switch-dataset.sh large      # 50項目版
./switch-dataset.sh xlarge   # 100項目版
./switch-dataset.sh xxlarge  # 200項目版
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

LightRAG はクエリ依存の局所サブグラフのみを構築します。

**確認方法**:

```bash
# GraphRAG: 探索ノード数を確認
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}}' \
  | jq '.metadata.nodes_explored'

# LightRAG: サブグラフのノード数を確認
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '.metadata.subgraph.total_nodes'
```

**期待される違い**: LightRAG の `subgraph.total_nodes` が GraphRAG の `nodes_explored` より少ない（軽量化の証拠）

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

**期待される傾向**（参考）:

- **KG**: すべての質問で正確（5/5）✅
- **RAG**: 小規模では一部成功、大規模で精度低下 ❌
- **GraphRAG**: データ量に依存せず安定（4/5 程度）⚠️
- **LightRAG**: 小規模では GraphRAG と同等、大規模で精度低下（ベクトル検索層の影響）⚠️

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

```bash
# ヘルスチェック
./evaluate.sh health

# 特定の質問で比較
./evaluate.sh compare "Acme Search の機能は？"

# 自動評価実行
./evaluate.sh eval
```

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
./switch-dataset.sh small    # 5項目版
./switch-dataset.sh medium   # 8項目版（デフォルト）
./switch-dataset.sh large    # 50項目版
```

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
