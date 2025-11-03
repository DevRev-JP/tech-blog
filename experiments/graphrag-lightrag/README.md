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

本実験では、データ量依存性を実証するため、複数のデータセットサイズを用意しています。

### 5 項目版（kg-no-rag と同じ）

`data/docs.jsonl` として提供。`kg-no-rag` 実験と同じデータセットを使用できます。最初の 5 エントリが含まれます。

**特徴**: 小規模データセットで、ベクトル検索の精度の限界を実証します。

### 8 項目版（デフォルト）

`data/docs-light.jsonl` として提供。8 エントリのテストデータで、以下の内容を含みます：

- 製品と機能の関係
- ポリシーと製品の関係
- 政策変更による影響

### 50 項目版

`data/docs-50.jsonl` として提供。最初の 5 エントリに加え、様々な製品・サービスの説明を追加した 50 エントリのデータセットです。

**特徴**: 同じドメインの情報を様々な表現で繰り返し記述することで、データ量増加に伴うベクトル検索の精度変化を実証します。

### 100 項目版

`data/docs-100.jsonl` として提供。50 項目版を 2 倍に拡張した 100 エントリのデータセットです。

**特徴**: より大きなデータセットで、ベクトル検索のノイズ増加と軽量化の効果をより明確に確認できます。

### 200 項目版

`data/docs-200.jsonl` として提供。50 項目版を 4 倍に拡張した 200 エントリのデータセットです。

**特徴**: 最大規模のデータセットで、データ量依存性の差を最も明確に確認できます。

**データセット切り替え**:

1. **スクリプトで切り替え（推奨・コンテナ再起動なし）**: `switch-dataset.sh` を使用して簡単に切り替えできます（後述）。

2. **動的切り替え**: 実行中に `/switch-dataset` エンドポイントで切り替えることも可能です。

3. **環境変数で指定**: 初回起動時に `docker-compose.yml` の `environment` セクションで `DATA_FILE` を指定します。

データセットは GraphRAG と LightRAG の両方で共通使用されます。

---

## ❓ テスト質問

実装を手元で実行して、GraphRAG と LightRAG の動作を確認できます。

**重要**: この質問セットは `kg-no-rag` 実験と同じ内容です。これにより、**KG（ナレッジグラフ）、RAG（ベクトル検索）、GraphRAG、LightRAG** の 4 つの手法を同じ質問で比較できます。

| ID          | 型   | 質問                                                                   | 期待値                         | 比較ポイント     |
| ----------- | ---- | ---------------------------------------------------------------------- | ------------------------------ | ---------------- |
| **Q1-集合** | 集合 | Acme が提供する全ユニークな機能は？                                    | Realtime Query, Semantic Index | 集合演算の確認   |
| **Q2-差分** | 対比 | Semantic Index を提供する製品で、Policy Audit を提供していない製品は？ | Acme Search                    | 論理的差分の確認 |
| **Q3-経路** | 経路 | Globex Graph を規制するポリシーは？                                    | POL-002                        | グラフ経路の確認 |
| **Q4-否定** | 否定 | Semantic Index を持たない機能は？                                      | Policy Audit, Realtime Query   | 論理否定の確認   |
| **Q5-交差** | 交差 | Acme と Globex の共通機能は？                                          | Semantic Index                 | 交差演算の確認   |

**注記**: `kg-no-rag` 実験と同じデータセット（5 項目版の `docs.jsonl`）と質問セットを使用することで、4 つの手法（KG、RAG、GraphRAG、LightRAG）を同じ条件で比較できます。

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

### 初期化完了の確認

ヘルスチェックエンドポイントで初期化完了を確認できます：

```bash
curl -sf http://localhost:8200/healthz
curl -sf http://localhost:8100/healthz
```

**初期化完了の判定**:

- 以下のような JSON レスポンスが返ってくれば準備完了です：
  ```json
  {
    "status": "ok",
    "service": "lightrag-api",
    "version": "0.1.0",
    "connections": { "neo4j": true, "qdrant": true, "embedding_model": true }
  }
  ```
- `connections` の各項目が `true` になっていれば、データベース接続と埋め込みモデルの準備が完了しています
- エラーが返る、または接続タイムアウトする場合は、まだ初期化中です（60-90 秒待ってから再試行してください）

初期化完了後、評価を実行できます：

```bash
# 自動評価実行
curl -s http://localhost:8100/eval | jq '.'
```

**評価結果の例**:

```json
{
  "summary": {
    "graphrag_ok": 5,
    "lightrag_ok": 5,
    "total": 5
  },
  "cases": [
    {
      "id": "Q1-集合",
      "ask": "Acme が提供する全ユニークな機能は？",
      "expected": ["Realtime Query", "Semantic Index"],
      "graphrag_nodes": ["POL-002", "Realtime Query", "POL-001", "Acme Search", "Policy Audit", "Semantic Index"],
      "lightrag_nodes": ["Globex Graph", "Realtime Query", "POL-001", "Acme Search", "Policy Audit", "Semantic Index"],
      "gr_ok": true,
      "lr_ok": true
    }
    ...
  ]
}
```

> **重要**: `/eval` の結果だけでは、**精度の比較**しかできません。両方が全問正解（5/5）の場合、一見違いがわかりません。
>
> **LightRAG の特徴（軽量化、階層化）を確認するには**、以下のいずれかの方法を使用してください：
>
> - 個別の質問で `/ask` を実行し、`metadata.subgraph` や `vector_nodes`/`graph_nodes` を確認
> - `/compare` エンドポイントで、同じ質問での探索ノード数やメタデータを比較
>
> 詳しくは「[比較結果の解釈](#-比較結果の解釈)」セクションを参照してください。

### 個別の質問で比較

**注意**: `/compare` だけでは**精度の違い（正答率）は確認できません**。精度を比較するには `/eval` を使用してください。

特定の質問で GraphRAG と LightRAG の**探索プロセスの違い**を確認する場合：

```bash
# 推奨: --data-urlencode を使用（日本語を含む質問でも安全）
curl -G "http://localhost:8100/compare" --data-urlencode "question=Acme Search の機能は？" | jq '.'
```

**`/compare` で確認できること**:

- `graphrag.metadata.nodes_explored`: GraphRAG が探索したノード数（例: 7）
- `lightrag.metadata.alpha_beta_ratio`: ベクトル検索とグラフ探索の重み比率（階層的検索の証拠）
- `lightrag.metadata.final_scores`: 各ノードの最終スコア（階層的検索の証拠）

**`/compare` では確認できないこと**:

- **精度の違い**: 期待値との一致度を確認するには `/eval` を使用
- **軽量化の違い**: `subgraph.total_nodes` や `vector_nodes` を確認するには個別に `/ask` を使用
- **階層的検索の詳細**: `vector_nodes` と `graph_nodes` の分離を確認するには個別に `/ask` を使用

**LightRAG の特徴を詳しく確認するには**、個別に `/ask` を実行してください。詳しくは「[比較結果の解釈](#-比較結果の解釈)」セクションを参照してください。

---

## 🔎 小規模環境での傾向と解釈（技術的注意）

このリポの実装は学習用の簡易構成です。実測では次のような傾向が観測されます。

- 精度（/eval）: 小規模〜中規模データでは GraphRAG と LightRAG が同点になることがある
- 圧縮（LightRAG の可変性）: `top_k` を小さくすると `vector_nodes`/`graph_nodes` が減り、回答長（`answer_len`）も短くなる（文脈予算を制御可能）
- 探索規模（GraphRAG）: `metadata.nodes_explored` で探索ノード数を確認でき、局所探索ではデータ量の影響が限定的に見えることがある
- レイテンシ（本実装）: 小規模では GraphRAG（簡易実装）の方が速く見える場合がある。LightRAG は埋め込み生成＋ベクトル検索の固定オーバーヘッドがあるため

重要な前提:

- 研究版 GraphRAG は「全体グラフ構築・コミュニティ要約」などの重い前処理を伴い、運用・更新コストが増大しやすい
- LightRAG は「クエリ毎の局所サブグラフ＋圧縮＋フィードバック」で、データ増大時も `top_k` と `depth` により計算を局所化しやすい（運用効率）

したがって、本実装での小規模比較でレイテンシが GraphRAG 有利に見えるとしても、LightRAG の価値は「文脈圧縮の可制御性」「局所化によるスケール対応」「フィードバックでの即時調整」といった運用面にある点に注意してください。実測は上のコマンドであなたの環境に合わせて再現できます。

---

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
>
> **重要な注意**: これらの質問は `kg-no-rag` 実験と同じものです。これにより、KG（ナレッジグラフ）、RAG（ベクトル検索）、GraphRAG、LightRAG の 4 つの手法を同じ質問で比較できます。

### Q1-集合: Acme が提供する全ユニークな機能は？

- **期待値**: `["Realtime Query", "Semantic Index"]`
- **比較ポイント**: 集合演算の確認
- **GraphRAG**: キーワードベースの簡易検索で機能を返す
- **LightRAG**: ベクトル検索 → グラフ探索の二層検索で機能を返す
- **違い**: LightRAG は `vector_nodes` と `graph_nodes` を分けて返す（階層的検索の証拠）
- **kg-no-rag との比較**: KG✅ RAG✅（小規模）→ RAG❌（大規模でノイズ増加）

### Q2-差分: Semantic Index を提供する製品で、Policy Audit を提供していない製品は？

- **期待値**: `["Acme Search"]`
- **比較ポイント**: 論理的差分（A かつ NOT B）の確認
- **GraphRAG**: キーワード検索ベースだが、論理的差分の処理は限定的
- **LightRAG**: ベクトル検索とグラフ探索を組み合わせるが、論理的否定条件は困難
- **違い**: 両手法とも論理的差分には課題がある（KG が最も得意とする領域）
- **kg-no-rag との比較**: KG✅ RAG❌（論理的差分はベクトル検索に不向き）

### Q3-経路: Globex Graph を規制するポリシーは？

- **期待値**: `["POL-002"]`
- **比較ポイント**: グラフ経路探索の確認（製品 → ポリシーの間接関係）
- **GraphRAG**: グラフ探索で経路をたどるが、簡易実装のため限定的
- **LightRAG**: ベクトル検索で関連文書を取得し、その中からポリシーを抽出
- **違い**: GraphRAG はグラフ探索に優れるが、LightRAG は間接関係の把握が困難な場合がある
- **kg-no-rag との比較**: KG✅ RAG❌（グラフ経路の間接関係を見落とす）

### Q4-否定: Semantic Index を持たない機能は？

- **期待値**: `["Policy Audit", "Realtime Query"]`
- **比較ポイント**: 論理否定条件の確認
- **GraphRAG**: キーワード検索ベースで否定条件の処理は限定的
- **LightRAG**: ベクトル検索では否定条件が曖昧になる
- **違い**: 両手法とも論理否定には課題がある（KG が最も得意とする領域）
- **kg-no-rag との比較**: KG✅ RAG❌（論理的否定条件が曖昧）

### Q5-交差: Acme と Globex の共通機能は？

- **期待値**: `["Semantic Index"]`
- **比較ポイント**: 交差演算（AND 検索）の確認
- **GraphRAG**: グラフ探索で両製品の機能を比較
- **LightRAG**: ベクトル検索とグラフ探索を組み合わせて共通機能を抽出
- **違い**: 両手法とも可能だが、GraphRAG の方が構造的比較に優れる
- **kg-no-rag との比較**: KG✅ RAG⚠️（小規模では成功、大規模では失敗）

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
# 推奨: --data-urlencode を使用（日本語を含む質問でも安全）
curl -G "http://localhost:8100/compare" --data-urlencode "question=Acme Search の機能は？" | jq '.'
```

**レスポンス構造**:

- `graphrag.metadata.nodes_explored`: GraphRAG が探索したノード数
- `lightrag.metadata.alpha_beta_ratio`: ベクトル検索とグラフ探索の重み比率（階層的検索の証拠）
- `lightrag.metadata.final_scores`: 各ノードの最終スコア（階層的検索の証拠）

> **注意**: `/compare` だけでは**精度の違い（正答率）は確認できません**。精度を比較するには `/eval` を使用してください。

**注意**: 初期化未完了の場合、JSON でないレスポンスが返る可能性があります。ヘルスチェックで準備完了を確認してください。

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

## 📝 テスト質問詳細（重複セクション - 参考用）

> **注記**: このセクションは上の「📝 テスト質問詳細」セクションと重複しています。詳細は上のセクションを参照してください。
>
> **重要な注意**: これらの質問は `kg-no-rag` 実験と同じものです。これにより、KG（ナレッジグラフ）、RAG（ベクトル検索）、GraphRAG、LightRAG の 4 つの手法を同じ質問で比較できます。

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

## 📖 記事に沿った GraphRAG vs LightRAG テストガイド

このセクションは、記事「[GraphRAG の限界と LightRAG の登場](../articles/graphrag-light-rag-2025-10.md)」を読みながら、実際に実験環境で動作確認できる比較ポイントをまとめたものです。

---

### 1. 「LightRAG とは ── 軽量化と階層化の設計思想」

#### ✅ 1-1. 軽量化（Lightweight）

**記事の説明**: グラフ全体ではなくクエリ依存のサブグラフを対象にする

**テスト方法**:

```bash
# LightRAG: クエリ依存のサブグラフのみを構築（depth=1で制限）
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Acme Search の機能は？",
    "top_k": 3,
    "depth": 1,
    "theta": 0.3
  }' | jq '.metadata.subgraph'

# GraphRAG: 全体グラフを探索（max_depth=3で広範囲探索）
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Acme Search の機能は？",
    "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}
  }' | jq
```

**期待される違い**: LightRAG の`subgraph.total_nodes`が GraphRAG より少ない

#### ✅ 1-2. 階層化（Hierarchical Retrieval）

**記事の説明**: ベクトルレベル（低レベル）とグラフレベル（高レベル）の二層検索

**テスト方法**:

```bash
# LightRAGの階層的検索を確認
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Globex Graph に関連する製品と機能は？",
    "top_k": 4,
    "depth": 2,
    "theta": 0.3
  }' | jq '{vector_nodes, graph_nodes, subgraph}'
```

**確認ポイント**:

- `vector_nodes`: ベクトル検索（低レベル）で取得したノード
- `graph_nodes`: グラフ探索（高レベル）で追加されたノード
- 2 つのリストが異なることを確認（階層的検索の証拠）

#### ⚠️ 1-3. 適応（Adaptive Feedback）

**記事の説明**: LLM の attention 重みをもとに、次回検索時のエッジ重みを動的調整

**現在の実装状況**:

- `/feedback`エンドポイントは実装済み
- ただし、LLM からの自動的な attention 重み取得は未実装（簡易実装のため）
- 手動でフィードバックを送信することで動作をシミュレート可能

**テスト方法**:

```bash
# 同じ質問を複数回実行
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Policy Audit に関連する製品は？", "top_k": 3, "depth": 2, "theta": 0.3}' | jq

# 手動でフィードバックを送信（実装では自動だが、簡易版では手動）
curl -X POST "http://localhost:8100/feedback" \
  -H "Content-Type: application/json" \
  -d '{"node_id": "Policy Audit", "weight": 1.5}'

# フィードバックログを確認
curl http://localhost:8100/feedback-log | jq
```

**注意**: 実装の完全版では、LLM の attention 重みが自動的に取得・反映されますが、現在の簡易実装では手動フィードバックが必要です。

---

### 2. 「内部構造とアルゴリズム」

#### ✅ 2-1. Retrieval Flow の 2 段階検索

**記事の説明**:

1. ベクトル検索層（Vector-level Retrieval）: top-k 文書を取得
2. グラフ探索層（Graph-level Retrieval）: 取得ノードを中心に ego-network を構築

**テスト方法**:

```bash
# パラメータを変えて、2段階検索の挙動を確認
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "製品と機能の関係を教えて",
    "top_k": 2,      # ベクトル検索で取得するノード数（低レベル）
    "depth": 2,      # グラフ探索の深さ（高レベル）
    "theta": 0.3     # スコア閾値
  }' | jq '{vector_nodes, graph_nodes: [.graph_nodes[] | {name: .name, type: .type}]}'
```

**確認ポイント**:

- `top_k`を小さくすると、ベクトル検索段階で取得するノードが減る
- `depth`を大きくすると、グラフ探索でより多くのノードが追加される
- `theta`を高くすると、低スコアのノードが除外される

#### ✅ 2-2. コンテキスト圧縮（Context Compression）

**記事の説明**: 取得したノード群を重要度で上位 k 件に圧縮（トークン入力量 30-50%削減）

**テスト方法**:

```bash
# top_kパラメータで圧縮度を確認
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "すべての製品と機能の関係", "top_k": 2, "depth": 3, "theta": 0.3}' \
  | jq '{answer, graph_nodes_count: (.graph_nodes | length)}'

# top_kを大きくすると、より多くのノードが返される
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "すべての製品と機能の関係", "top_k": 10, "depth": 3, "theta": 0.3}' \
  | jq '{answer, graph_nodes_count: (.graph_nodes | length)}'
```

---

### 3. 「GraphRAG との定量的比較と改善点」

#### ✅ 3-1. 構造探索: 全体グラフトラバース vs クエリ依存サブグラフ

**記事の改善点**: 検索計算量を O(n²)→O(k log n)に削減

**テスト方法**:

```bash
# GraphRAG: 全体グラフを探索（max_depthを大きくすると探索範囲が広がる）
time curl -s -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}}' > /dev/null

# LightRAG: クエリ依存サブグラフのみ（depthで制限）
time curl -s -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "top_k": 4, "depth": 2, "theta": 0.3}' > /dev/null
```

**確認ポイント**: LightRAG の方がレスポンスタイムが短いことを確認（簡易実装のため、大きな差は出ない可能性あり）

#### ✅ 3-2. コンテキスト処理: 静的連結 vs 動的圧縮

**記事の改善点**: トークン効率化・応答速度向上

**テスト方法**:

```bash
# GraphRAG: 静的連結（すべての関連ノードを含む）
curl -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "graph_walk": {"max_depth": 2, "prune_threshold": 0.2}}' \
  | jq '.answer' | wc -w

# LightRAG: 動的圧縮（top_kで制限）
curl -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "top_k": 3, "depth": 2, "theta": 0.3}' \
  | jq '.answer' | wc -w
```

**確認ポイント**: LightRAG の回答がよりコンパクト（単語数が少ない）

---

## 🎯 総合比較テスト

記事全体を通して理解できる主な違いを一度に確認するテスト：

```bash
#!/bin/bash

echo "=== GraphRAG vs LightRAG 総合比較 ==="

echo -e "\n【テスト1: 階層的検索】"
echo "LightRAG: ベクトル検索→グラフ探索"
curl -s -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search", "top_k": 3, "depth": 2, "theta": 0.3}' \
  | jq '{vector_nodes, graph_node_count: (.graph_nodes | length)}'

echo -e "\n【テスト2: 局所サブグラフ】"
curl -s -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "top_k": 3, "depth": 1, "theta": 0.3}' \
  | jq '.metadata.subgraph'

echo -e "\n【テスト3: コンテキスト圧縮】"
echo "LightRAG (top_k=2):"
curl -s -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品と機能", "top_k": 2, "depth": 2, "theta": 0.3}' \
  | jq '{answer_length: (.answer | length), node_count: (.graph_nodes | length)}'

echo "GraphRAG (全ノード):"
curl -s -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品と機能", "graph_walk": {"max_depth": 2, "prune_threshold": 0.2}}' \
  | jq '{answer_length: (.answer | length)}'
```

---

## ⚠️ 現在の実装の制限事項

記事で説明されている機能のうち、現在の簡易実装では以下の制限があります：

1. **自動的な attention 重み取得**: LLM からの自動取得は未実装。手動で`/feedback`エンドポイントを使用する必要があります。
2. **グラフ一貫性の検証**: 部分再構築を繰り返した際の整合性チェックは未実装。
3. **意味推論**: 記事で言及されている「LLM + 重み最適化」による部分的推論強化は、LLM 統合が未完了のため完全にはテストできません。
4. **ベンチマーク数値**: 記事の「O(n²)→O(k log n)」などの計算量改善は概念的に確認できますが、大規模データでの実測値は未実装です。

---

## 📝 補足: 実装の完全版との違い

現在の実装は**簡易版**であり、以下の機能は今後追加予定です：

- Microsoft GraphRAG CLI との統合（GraphRAG 側）
- 完全な LLM 統合と attention 重みの自動取得（LightRAG 側）
- オンライン正規化アルゴリズム（グラフ一貫性の検証）
- 大規模データセットでのベンチマーク

ただし、記事で説明されている**主な設計思想やアルゴリズムの違い**は、現在の実装でも十分に確認できます。

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

`switch-dataset.sh` スクリプトを使用すると、**コンテナ再起動なしで**簡単にデータセットを切り替えてテストできます：

```bash
# コンテナが起動している必要があります（初回のみ）
docker compose up -d

# 小規模版（5個）に切り替え
./switch-dataset.sh small

# 中規模版（8個）に切り替え
./switch-dataset.sh medium

# 大規模版（50個）に切り替え
./switch-dataset.sh large

# 超大規模版（100個）に切り替え
./switch-dataset.sh xlarge

# 超超大規模版（200個）に切り替え
./switch-dataset.sh xxlarge

# 小規模と大規模を比較（コンテナ再起動なし）
./switch-dataset.sh compare
```

**注意**: スクリプトはコンテナを再起動せず、実行中のコンテナに対して `/switch-dataset` エンドポイントを呼び出してデータを切り替えます。初回のみ `docker compose up -d` でコンテナを起動してください。

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

1. **小規模（5 個）と大規模（50 個）の比較**: `./switch-dataset.sh compare` を実行すると、自動的に両方をテストして結果を比較表示します（コンテナ再起動なし）。

2. **より大きなデータセットで比較**: 100 個、200 個のデータセットを使用して、より明確に違いを確認できます：

```bash
# コンテナ起動（初回のみ）
docker compose up -d

# 初期化完了まで待機
curl -sf http://localhost:8100/healthz

# 小規模版（5個）でテスト
./switch-dataset.sh small
# 結果を確認・記録

# 超大規模版（100個）でテスト
./switch-dataset.sh xlarge
# 結果を確認・記録

# 超超大規模版（200個）でテスト
./switch-dataset.sh xxlarge
# 結果を確認・記録
```

**期待される動作**:

- GraphRAG: データ量に依存せず、グラフ構造に基づく検索のため安定した精度を維持
- LightRAG: データ量が増えると、ベクトル検索段階でノイズが増え、精度が低下する可能性がある（特に 100 個、200 個のデータセットで差が明確になる）

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
