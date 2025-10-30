#!/bin/bash

# GraphRAG vs LightRAG 評価スクリプト

set -e

GRAPHRAG_URL="http://localhost:8200"
LIGHTRAG_URL="http://localhost:8100"

# 色付き出力用
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ヘルパー関数
print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

check_health() {
    local url=$1
    local name=$2
    echo -n "Checking $name... "
    if curl -sf "$url/healthz" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

case "$1" in
  health)
    print_header "ヘルスチェック"
    
    if check_health "$GRAPHRAG_URL" "GraphRAG API"; then
        echo "  GraphRAG connections:"
        curl -s "$GRAPHRAG_URL/connections" | jq '.' || echo "  (情報取得失敗)"
    fi
    
    echo ""
    
    if check_health "$LIGHTRAG_URL" "LightRAG API"; then
        echo "  LightRAG connections:"
        curl -s "$LIGHTRAG_URL/connections" | jq '.' || echo "  (情報取得失敗)"
    fi
    
    echo ""
    echo "Neo4j: http://localhost:7474 (neo4j/password)"
    echo "Qdrant: http://localhost:6333"
    ;;
    
  compare)
    print_header "GraphRAG vs LightRAG 比較"
    
    if [ -z "$2" ]; then
        echo "使用方法: $0 compare \"質問文\""
        echo "例: $0 compare \"製品一覧\""
        exit 1
    fi
    
    question="$2"
    echo "質問: $question"
    echo ""
    
    echo "結果を取得中..."
    result=$(curl -s "$LIGHTRAG_URL/compare?question=$(echo "$question" | jq -sRr @uri)" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$result" ]; then
        echo "$result" | jq '.'
    else
        echo -e "${RED}エラー: 比較リクエストが失敗しました${NC}"
        exit 1
    fi
    ;;
    
  eval)
    print_header "自動評価実行"
    
    echo "questions.json からテスト質問を読み込んで評価します..."
    echo ""
    
    result=$(curl -s "$LIGHTRAG_URL/eval" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$result" ]; then
        echo "$result" | jq '.'
        
        # サマリーを強調表示
        echo ""
        echo "=========================================="
        echo "サマリー"
        echo "=========================================="
        echo "$result" | jq -r '
          "GraphRAG: \(.summary.graphrag_ok)/\(.summary.total)\nLightRAG: \(.summary.lightrag_ok)/\(.summary.total)"
        '
    else
        echo -e "${RED}エラー: 評価リクエストが失敗しました${NC}"
        echo "ヒント: サービスが起動しているか確認してください ($0 health)"
        exit 1
    fi
    ;;
    
  *)
    echo "GraphRAG vs LightRAG 評価スクリプト"
    echo ""
    echo "使用方法:"
    echo "  $0 health              # 両APIのヘルスチェック"
    echo "  $0 compare \"質問文\"   # GraphRAG と LightRAG を比較"
    echo "  $0 eval                # 自動評価を実行（questions.json使用）"
    echo ""
    echo "例:"
    echo "  $0 health"
    echo "  $0 compare \"製品一覧\""
    echo "  $0 eval"
    exit 1
    ;;
esac



