#!/bin/bash

# Formal Layer 評価スクリプト

set -e

SQL_URL="http://localhost:8300"
KG_URL="http://localhost:8400"
POLICY_URL="http://localhost:8500"
OPTIMIZATION_URL="http://localhost:8600"

# 色付き出力用
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

test_sql_layer() {
    print_header "SQL Layer (Value Layer) テスト"
    
    echo "1. 未処理請求の取得 (CUST-123, mode=open)"
    curl -s -X POST "$SQL_URL/query" \
      -H "Content-Type: application/json" \
      -d '{"customerId": "CUST-123", "mode": "open"}' | jq '.'
    
    echo ""
    echo "2. 全請求の取得 (CUST-123, mode=all)"
    curl -s -X POST "$SQL_URL/query" \
      -H "Content-Type: application/json" \
      -d '{"customerId": "CUST-123", "mode": "all"}' | jq '.'
    
    echo ""
    echo "3. 全請求データの取得"
    curl -s "$SQL_URL/billing" | jq '.'
}

test_kg_layer() {
    print_header "KG Layer (Semantic Layer) テスト"
    
    echo "1. 顧客のSLA情報を取得 (CUST-123)"
    curl -s -X POST "$KG_URL/query" \
      -H "Content-Type: application/json" \
      -d '{"customer_id": "CUST-123", "path_type": "sla"}' | jq '.'
    
    echo ""
    echo "2. グラフ全体の取得"
    curl -s "$KG_URL/graph" | jq '.'
}

test_policy_layer() {
    print_header "Policy Layer (Policy Layer) テスト"
    
    echo "1. プラチナ顧客 + クリティカル課題 → High優先度"
    curl -s -X POST "$POLICY_URL/evaluate" \
      -H "Content-Type: application/json" \
      -d '{"customer_tier": "Platinum", "issue": "Critical"}' | jq '.'
    
    echo ""
    echo "2. ゴールド顧客 + クリティカル課題 → Medium優先度"
    curl -s -X POST "$POLICY_URL/evaluate" \
      -H "Content-Type: application/json" \
      -d '{"customer_tier": "Gold", "issue": "Critical"}' | jq '.'
    
    echo ""
    echo "3. プラチナ顧客 + 高重要度課題 → Medium優先度"
    curl -s -X POST "$POLICY_URL/evaluate" \
      -H "Content-Type: application/json" \
      -d '{"customer_tier": "Platinum", "issue": "High"}' | jq '.'
    
    echo ""
    echo "4. シルバー顧客 + 中重要度課題 → Low優先度（デフォルト）"
    curl -s -X POST "$POLICY_URL/evaluate" \
      -H "Content-Type: application/json" \
      -d '{"customer_tier": "Silver", "issue": "Medium"}' | jq '.'
}

test_optimization_layer() {
    print_header "Optimization Layer (Optimization Layer) テスト"
    
    echo "1. タスク割り当て問題（記事の例）"
    curl -s -X POST "$OPTIMIZATION_URL/assign" \
      -H "Content-Type: application/json" \
      -d '{
        "agents": ["A", "B"],
        "tasks": ["T1", "T2", "T3"],
        "max_tasks_per_agent": 2
      }' | jq '.'
    
    echo ""
    echo "2. サンプルスケジューリング"
    curl -s -X POST "$OPTIMIZATION_URL/schedule" | jq '.'
}

case "$1" in
  health)
    print_header "ヘルスチェック"
    
    check_health "$SQL_URL" "SQL Layer"
    check_health "$KG_URL" "KG Layer"
    check_health "$POLICY_URL" "Policy Layer"
    check_health "$OPTIMIZATION_URL" "Optimization Layer"
    
    echo ""
    echo "Neo4j: http://localhost:7474 (neo4j/password)"
    echo "OPA: http://localhost:8181"
    ;;
    
  sql)
    if check_health "$SQL_URL" "SQL Layer"; then
        test_sql_layer
    else
        echo -e "${RED}SQL Layer が起動していません${NC}"
        exit 1
    fi
    ;;
    
  kg)
    if check_health "$KG_URL" "KG Layer"; then
        test_kg_layer
    else
        echo -e "${RED}KG Layer が起動していません${NC}"
        exit 1
    fi
    ;;
    
  policy)
    if check_health "$POLICY_URL" "Policy Layer"; then
        test_policy_layer
    else
        echo -e "${RED}Policy Layer が起動していません${NC}"
        exit 1
    fi
    ;;
    
  optimization)
    if check_health "$OPTIMIZATION_URL" "Optimization Layer"; then
        test_optimization_layer
    else
        echo -e "${RED}Optimization Layer が起動していません${NC}"
        exit 1
    fi
    ;;
    
  all)
    print_header "全形式レイヤのテスト"
    
    if check_health "$SQL_URL" "SQL Layer"; then
        test_sql_layer
    fi
    
    echo ""
    if check_health "$KG_URL" "KG Layer"; then
        test_kg_layer
    fi
    
    echo ""
    if check_health "$POLICY_URL" "Policy Layer"; then
        test_policy_layer
    fi
    
    echo ""
    if check_health "$OPTIMIZATION_URL" "Optimization Layer"; then
        test_optimization_layer
    fi
    ;;
    
  *)
    echo "Formal Layer 評価スクリプト"
    echo ""
    echo "使用方法:"
    echo "  $0 health                    # 全APIのヘルスチェック"
    echo "  $0 sql                       # SQL Layer のテスト"
    echo "  $0 kg                        # KG Layer のテスト"
    echo "  $0 policy                    # Policy Layer のテスト"
    echo "  $0 optimization              # Optimization Layer のテスト"
    echo "  $0 all                       # 全形式レイヤのテスト"
    echo ""
    echo "例:"
    echo "  $0 health"
    echo "  $0 sql"
    echo "  $0 all"
    exit 1
    ;;
esac

