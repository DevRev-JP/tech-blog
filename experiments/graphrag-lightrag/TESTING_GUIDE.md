# 記事に沿った GraphRAG vs LightRAG テストガイド

このドキュメントは、記事「[GraphRAG の限界と LightRAG の登場](../articles/graphrag-light-rag-2025-10.md)」を読みながら、実際に実験環境で動作確認できる比較ポイントをまとめたものです。

---

## 📖 記事の章ごとのテスト方法

### 1. 「LightRAG とは ── 軽量化と階層化の設計思想」

記事では 3 つの設計思想が説明されています。それぞれをテストできます：

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

記事の比較表に沿って、実際の違いを確認できます：

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
