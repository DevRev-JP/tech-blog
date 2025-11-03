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

# データセット切り替え関数
switch_dataset() {
    local dataset=$1
    local file=""
    local name=""
    
    case "$dataset" in
      small)
        file="data/docs.jsonl"
        name="小規模版（5個）"
        ;;
      medium)
        file="data/docs-light.jsonl"
        name="中規模版（8個）"
        ;;
      size50)
        file="data/docs-50.jsonl"
        name="中規模版（約50ノード）"
        ;;
      size300)
        file="data/docs-300.jsonl"
        name="大規模版（約300ノード）"
        ;;
      size500)
        file="data/docs-500.jsonl"
        name="超大規模版（約500ノード）"
        ;;
      size1000)
        file="data/docs-1000.jsonl"
        name="最大規模版（約1000ノード）"
        ;;
      *)
        echo -e "${RED}エラー: 未知のデータセット名: $dataset${NC}"
        echo "利用可能なデータセット: small, medium, size50, size300, size500, size1000"
        return 1
        ;;
    esac
    
    echo -e "${YELLOW}🔄 $name に切り替え中...${NC}"
    
    # GraphRAG と LightRAG の両方を切り替え
    curl -s -X POST "$GRAPHRAG_URL/switch-dataset?file=$file" > /dev/null 2>&1
    curl -s -X POST "$LIGHTRAG_URL/switch-dataset?file=$file" > /dev/null 2>&1
    
    echo -e "${YELLOW}⏳ データシード完了待機中（10秒）...${NC}"
    sleep 10
    
    # ヘルスチェックで確認
    if check_health "$GRAPHRAG_URL" "GraphRAG API" && check_health "$LIGHTRAG_URL" "LightRAG API"; then
        echo -e "${GREEN}✅ 切り替え完了: $name${NC}"
        return 0
    else
        echo -e "${RED}❌ ヘルスチェックに失敗しました${NC}"
        return 1
    fi
}

# 評価実行関数
run_eval() {
    local dataset_name="${1:-}"
    if [ -n "$dataset_name" ]; then
        if ! switch_dataset "$dataset_name"; then
            exit 1
        fi
        echo ""
    fi
    
    print_header "自動評価実行${dataset_name:+（$dataset_name）}"
    
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
    # データセット名が指定されている場合は切り替えてから評価
    if [ -n "$2" ]; then
        run_eval "$2"
    else
        run_eval ""
    fi
    ;;
    
  eval-all)
    print_header "全データセットで比較評価"
    
    echo "複数のデータセットで順番に評価を実行します..."
    echo ""
    
    # データセット一覧
    datasets=("small" "size50" "size300" "size500" "size1000")
    
    # 結果を一時ファイルに保存（連想配列の代わり）
    result_file=$(mktemp)
    
    for dataset in "${datasets[@]}"; do
        echo ""
        echo "=========================================="
        echo "データセット: $dataset"
        echo "=========================================="
        
        if switch_dataset "$dataset"; then
            echo ""
            result=$(curl -s "$LIGHTRAG_URL/eval" 2>/dev/null)
            
            if [ $? -eq 0 ] && [ -n "$result" ]; then
                gr_ok=$(echo "$result" | jq -r '.summary.graphrag_ok')
                lr_ok=$(echo "$result" | jq -r '.summary.lightrag_ok')
                total=$(echo "$result" | jq -r '.summary.total')
                
                # 結果を一時ファイルに保存
                echo "$dataset|$gr_ok|$lr_ok|$total" >> "$result_file"
                
                echo -e "${GREEN}結果: GraphRAG=$gr_ok/$total, LightRAG=$lr_ok/$total${NC}"
            else
                echo -e "${RED}評価に失敗しました${NC}"
                echo "$dataset|0|0|5" >> "$result_file"
            fi
        else
            echo -e "${RED}データセット切り替えに失敗しました${NC}"
            echo "$dataset|0|0|5" >> "$result_file"
        fi
        
        echo ""
        sleep 2
    done
    
    # まとめ表示
    echo ""
    echo "=========================================="
    echo "比較結果まとめ"
    echo "=========================================="
    printf "%-15s | %-10s | %-10s\n" "データセット" "GraphRAG" "LightRAG"
    echo "----------------------------------------"
    while IFS='|' read -r dataset gr_ok lr_ok total; do
        printf "%-15s | %-10s | %-10s\n" "$dataset" "$gr_ok/$total" "$lr_ok/$total"
    done < "$result_file"
    echo ""
    
    # 一時ファイルを削除
    rm -f "$result_file"
    ;;
    
  *)
    echo "GraphRAG vs LightRAG 評価スクリプト"
    echo ""
    echo "使用方法:"
    echo "  $0 health                    # 両APIのヘルスチェック"
    echo "  $0 compare \"質問文\"         # GraphRAG と LightRAG を比較"
    echo "  $0 eval [dataset]            # 自動評価を実行（questions.json使用）"
    echo "  $0 eval-all                 # 全データセットで順番に評価"
    echo ""
    echo "データセット指定:"
    echo "  $0 eval small                # 小規模版（5個）で評価"
    echo "  $0 eval size50               # 中規模版（約50ノード）で評価"
    echo "  $0 eval size300              # 大規模版（約300ノード）で評価"
    echo "  $0 eval size500              # 超大規模版（約500ノード）で評価"
    echo "  $0 eval size1000             # 最大規模版（約1000ノード）で評価"
    echo ""
    echo "利用可能なデータセット: small, medium, size50, size300, size500, size1000"
    echo ""
    echo "例:"
    echo "  $0 health"
    echo "  $0 compare \"製品一覧\""
    echo "  $0 eval                      # 現在のデータセットで評価"
    echo "  $0 eval size300              # 300ノード版に切り替えて評価"
    echo "  $0 eval-all                  # 全データセットで比較評価"
    exit 1
    ;;
esac






