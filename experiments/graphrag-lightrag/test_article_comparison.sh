#!/bin/bash
# 記事の主な比較ポイントをテストするスクリプト

echo "========================================="
echo "記事「GraphRAG vs LightRAG」の比較テスト"
echo "========================================="

echo -e "\n【1. 階層的検索の違い - LightRAGの二層検索】"
echo "LightRAGはベクトル検索（低レベル）→グラフ探索（高レベル）の2段階"
curl -s -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "top_k": 3, "depth": 2, "theta": 0.3}' \
  | jq '{answer, vector_nodes, graph_nodes: [.graph_nodes[] | .name]}'

echo -e "\n【2. GraphRAGのグラフ探索】"
echo "GraphRAGはグラフ全体を探索（簡易実装）"
curl -s -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Acme Search の機能は？", "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}}' \
  | jq '{answer, metadata: {pipeline, max_depth}}'

echo -e "\n【3. 局所サブグラフの軽量化（LightRAGの特徴）】"
echo "LightRAGはクエリ依存のサブグラフのみを構築"
curl -s -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Globex Graph と関連する製品は？", "top_k": 4, "depth": 2, "theta": 0.3}' \
  | jq '{answer, metadata: {subgraph: {total_nodes, depth}}}'

echo -e "\n【4. コンテキスト圧縮（LightRAG）vs 静的連結（GraphRAG）】"
echo "LightRAG: top_kで圧縮"
echo "GraphRAG: すべての関連ノードを返す"
curl -s -X POST "http://localhost:8100/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "top_k": 2, "depth": 1, "theta": 0.3}' \
  | jq '{answer, graph_nodes: [.graph_nodes[] | .name] | length}'
curl -s -X POST "http://localhost:8200/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "製品一覧", "graph_walk": {"max_depth": 2, "prune_threshold": 0.2}}' \
  | jq '{answer}'

echo -e "\n【5. フィードバックループ（LightRAG固有）】"
echo "同じ質問を複数回実行して確認（簡易実装のため手動フィードバックが必要）"
for i in {1..2}; do
  echo "--- 実行 $i ---"
  curl -s -X POST "http://localhost:8100/ask" \
    -H "Content-Type: application/json" \
    -d '{"question": "Policy Audit に関連する製品は？", "top_k": 3, "depth": 2, "theta": 0.3}' \
    | jq -r '.answer'
done
echo "--- フィードバックログ ---"
curl -s http://localhost:8100/feedback-log | jq .

echo -e "\n【テスト完了】"
