#!/bin/bash

# 統合シナリオ: 顧客サポートフローを 4 レイヤで一気通貫で処理

set -e

SQL_URL="http://localhost:8300"
KG_URL="http://localhost:8400"
POLICY_URL="http://localhost:8500"
OPTIMIZATION_URL="http://localhost:8600"
LLM_MOCK_URL="http://localhost:8700"

# 色付き出力用
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

# デフォルトの入力（自然言語）
CUSTOMER_QUERY="${1:-CUST-123 の未処理請求を取得して}"
ISSUE_DESCRIPTION="${2:-重要なお客様にとって重要度が高い問題が発生しています}"

print_header "統合シナリオ: 顧客サポートフロー"

echo "入力:"
echo "  顧客クエリ: $CUSTOMER_QUERY"
echo "  課題説明: $ISSUE_DESCRIPTION"
echo ""

# Step 1: LLM が自然言語から構造化データを抽出
print_step "Step 1: LLM が自然言語から構造化データを抽出"

echo "  自然言語: \"$CUSTOMER_QUERY\""
billing_query=$(curl -s -X POST "$LLM_MOCK_URL/extract-billing-query" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$CUSTOMER_QUERY\"}")

echo "  抽出結果:"
echo "$billing_query" | jq '.'
customer_id=$(echo "$billing_query" | jq -r '.customerId')

echo ""

# Step 2: SQL Layer で顧客の契約情報を取得
print_step "Step 2: SQL Layer で顧客の契約情報を取得"

billing_data=$(curl -s -X POST "$SQL_URL/query" \
  -H "Content-Type: application/json" \
  -d "$billing_query")

echo "  請求データ:"
echo "$billing_data" | jq '.results'

echo ""

# Step 3: KG Layer で顧客の契約プランと SLA 情報を取得
print_step "Step 3: KG Layer で顧客の契約プランと SLA 情報を取得"

# Step 3a: LLM が自然言語から経路タイプを選択
echo "  自然言語クエリ: \"顧客のSLA情報が知りたい\""
kg_path_request=$(curl -s -X POST "$LLM_MOCK_URL/extract-kg-path" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"顧客のSLA情報が知りたい\"}")

echo "  選択された経路タイプ:"
echo "$kg_path_request" | jq '.'
path_type=$(echo "$kg_path_request" | jq -r '.path_type')

echo ""

# Step 3b: KG Layer で経路テンプレートに基づいてクエリ実行
echo "  利用可能な経路テンプレート:"
curl -s -X GET "$KG_URL/paths" | jq '.paths[] | {path_type, description, use_case}'

echo ""
echo "  実行する経路: $path_type"

kg_data=$(curl -s -X POST "$KG_URL/query" \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\": \"$customer_id\", \"path_type\": \"$path_type\"}")

echo "  SLA 情報:"
echo "$kg_data" | jq '.results'

# 顧客ティアを取得（簡易版: SLA priority から推測）
sla_priority=$(echo "$kg_data" | jq -r '.results[0].priority // "Medium"')
if [ "$sla_priority" = "High" ]; then
    customer_tier="Platinum"
elif [ "$sla_priority" = "Medium" ]; then
    customer_tier="Platinum"  # 重要なお客様
else
    customer_tier="Silver"
fi

echo ""

# Step 4: Policy Layer で顧客ティアと課題重要度から優先度を判定
print_step "Step 4: Policy Layer で優先度を判定"

echo "  課題説明: \"$ISSUE_DESCRIPTION\""
policy_request=$(curl -s -X POST "$LLM_MOCK_URL/extract-policy-request" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$ISSUE_DESCRIPTION\"}")

# 顧客ティアを上書き（KG から取得した値を使用）
policy_request=$(echo "$policy_request" | jq ".customer_tier = \"$customer_tier\"")

echo "  ポリシーリクエスト:"
echo "$policy_request" | jq '.'

policy_result=$(curl -s -X POST "$POLICY_URL/evaluate" \
  -H "Content-Type: application/json" \
  -d "$policy_request")

echo "  判定結果:"
echo "$policy_result" | jq '.priority'

priority=$(echo "$policy_result" | jq -r '.priority')

echo ""

# Step 5: Optimization Layer でエージェントへの割り当てを最適化
print_step "Step 5: Optimization Layer でエージェントへの割り当てを最適化"

task_id="TASK-$(date +%s)"
optimization_result=$(curl -s -X POST "$OPTIMIZATION_URL/assign" \
  -H "Content-Type: application/json" \
  -d "{
    \"agents\": [\"Agent1\", \"Agent2\", \"Agent3\"],
    \"tasks\": [\"$task_id\"],
    \"max_tasks_per_agent\": 2
  }")

echo "  割り当て結果:"
echo "$optimization_result" | jq '.assignments'

assigned_agent=$(echo "$optimization_result" | jq -r '.assignments[0].agent')

echo ""

# Step 6: LLM が構造化データから自然言語の応答を生成
print_step "Step 6: LLM が構造化データから自然言語の応答を生成"

response_data=$(curl -s -X POST "$LLM_MOCK_URL/format-response" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"$customer_id\",
    \"priority\": \"$priority\",
    \"assigned_agent\": \"$assigned_agent\",
    \"billing_count\": $(echo "$billing_data" | jq '.count')
  }")

echo "  応答:"
echo "$response_data" | jq -r '.text'

echo ""

# まとめ
print_header "処理完了"

echo -e "${GREEN}✓ 顧客: $customer_id${NC}"
echo -e "${GREEN}✓ 優先度: $priority${NC}"
echo -e "${GREEN}✓ 割り当てエージェント: $assigned_agent${NC}"
echo ""

echo "このフローでは、4 つの形式レイヤが連携して安全に処理を行いました:"
echo "  1. SQL Layer: 値の整合性を保証"
echo "  2. KG Layer: 意味構造と関係推論"
echo "  3. Policy Layer: 判断の厳密化"
echo "  4. Optimization Layer: 最適解探索"
echo ""
echo "LLM は自然言語 ↔ 構造化データの変換のみを担当し、"
echo "判断・整合性・推論・最適化は形式レイヤが決定性を持って実行しました。"

