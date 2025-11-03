#!/bin/bash

# データセット切り替えスクリプト（コンテナ再起動なしで動的切り替え）
# 使い方:
#   ./switch-dataset.sh small   # 小規模版（5個）に切り替え
#   ./switch-dataset.sh medium  # 中規模版（8個）に切り替え
#   ./switch-dataset.sh large   # 大規模版（50個）に切り替え
#   ./switch-dataset.sh xlarge  # 超大規模版（100個）に切り替え
#   ./switch-dataset.sh xxlarge # 超超大規模版（200個）に切り替え
#   ./switch-dataset.sh compare # 小規模と大規模を比較（コンテナ再起動なし）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# コンテナが起動しているか確認
check_containers() {
    if ! curl -sf http://127.0.0.1:8200/healthz > /dev/null 2>&1; then
        echo "❌ GraphRAG API が起動していません。先に docker compose up -d でコンテナを起動してください。"
        exit 1
    fi
    if ! curl -sf http://127.0.0.1:8100/healthz > /dev/null 2>&1; then
        echo "❌ LightRAG API が起動していません。先に docker compose up -d でコンテナを起動してください。"
        exit 1
    fi
}

switch_dataset() {
    local file=$1
    local name=$2
    
    echo "🔄 $name に切り替え中..."
    
    # GraphRAG と LightRAG の両方を切り替え
    curl -s -X POST "http://127.0.0.1:8200/switch-dataset?file=$file" > /dev/null
    curl -s -X POST "http://127.0.0.1:8100/switch-dataset?file=$file" > /dev/null
    
    echo "⏳ データシード完了待機中（5秒）..."
    sleep 5
    
    echo "✅ 切り替え完了: $name"
    echo ""
}

case "${1:-small}" in
  small)
    check_containers
    switch_dataset "data/docs.jsonl" "小規模版（5個）"
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8100/eval | jq '{summary: .summary, cases: [.cases[] | {id, gr_ok, lr_ok}]}'
    ;;

  medium)
    check_containers
    switch_dataset "data/docs-light.jsonl" "中規模版（8個）"
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8100/eval | jq '{summary: .summary, cases: [.cases[] | {id, gr_ok, lr_ok}]}'
    ;;

  large)
    check_containers
    switch_dataset "data/docs-50.jsonl" "大規模版（50個）"
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8100/eval | jq '{summary: .summary, cases: [.cases[] | {id, gr_ok, lr_ok}]}'
    ;;

  xlarge)
    check_containers
    switch_dataset "data/docs-100.jsonl" "超大規模版（100個）"
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8100/eval | jq '{summary: .summary, cases: [.cases[] | {id, gr_ok, lr_ok}]}'
    ;;

  xxlarge)
    check_containers
    switch_dataset "data/docs-200.jsonl" "超超大規模版（200個）"
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8100/eval | jq '{summary: .summary, cases: [.cases[] | {id, gr_ok, lr_ok}]}'
    ;;

  compare)
    check_containers
    echo "📊 小規模版と大規模版を比較テスト開始..."
    echo ""

    echo "=== 小規模版（5個） ==="
    switch_dataset "data/docs.jsonl" "小規模版（5個）"
    SMALL_GR=$(curl -s http://127.0.0.1:8100/eval | jq '.summary.graphrag_ok')
    SMALL_LR=$(curl -s http://127.0.0.1:8100/eval | jq '.summary.lightrag_ok')
    echo "✅ 小規模版: GraphRAG=$SMALL_GR/5, LightRAG=$SMALL_LR/5"
    echo ""

    echo "=== 大規模版（50個） ==="
    switch_dataset "data/docs-50.jsonl" "大規模版（50個）"
    LARGE_GR=$(curl -s http://127.0.0.1:8100/eval | jq '.summary.graphrag_ok')
    LARGE_LR=$(curl -s http://127.0.0.1:8100/eval | jq '.summary.lightrag_ok')
    echo "✅ 大規模版: GraphRAG=$LARGE_GR/5, LightRAG=$LARGE_LR/5"
    echo ""

    echo "📊 結果比較:"
    echo "┌─────────┬──────────┬──────────┐"
    echo "│ バージョン │ GraphRAG │ LightRAG │"
    echo "├─────────┼──────────┼──────────┤"
    echo "│ 小規模(5個) │   $SMALL_GR/5   │   $SMALL_LR/5   │"
    echo "│ 大規模(50個)│   $LARGE_GR/5   │   $LARGE_LR/5   │"
    echo "└─────────┴──────────┴──────────┘"
    ;;

  *)
    echo "使い方:"
    echo "  $0 small     # 小規模版（5個）に切り替え"
    echo "  $0 medium    # 中規模版（8個）に切り替え"
    echo "  $0 large     # 大規模版（50個）に切り替え"
    echo "  $0 xlarge    # 超大規模版（100個）に切り替え"
    echo "  $0 xxlarge   # 超超大規模版（200個）に切り替え"
    echo "  $0 compare   # 小規模と大規模を比較（コンテナ再起動なし）"
    echo ""
    echo "注意: コンテナが起動している必要があります（docker compose up -d）"
    exit 1
    ;;
esac

