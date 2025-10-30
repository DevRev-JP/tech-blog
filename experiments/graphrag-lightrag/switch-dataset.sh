#!/bin/bash

# データセット切り替えスクリプト（kg-no-rag と同じ形式）
# 使い方:
#   ./switch-dataset.sh small   # 小規模版（5個）
#   ./switch-dataset.sh medium  # 中規模版（8個）
#   ./switch-dataset.sh large   # 大規模版（50個）
#   ./switch-dataset.sh compare # 両方実行して結果を比較

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# docker コマンドを検出（エイリアス回避のため command -v を使用）
if command -v docker >/dev/null 2>&1; then
    DOCKER_CMD="docker"
elif command -v podman >/dev/null 2>&1; then
    DOCKER_CMD="podman"
else
    echo "❌ docker または podman が見つかりません"
    exit 1
fi

case "${1:-small}" in
  small)
    echo "📊 小規模版（5個）でテスト開始..."
    $DOCKER_CMD compose down -v
    DATA_FILE=data/docs.jsonl $DOCKER_CMD compose up --detach
    echo "⏳ 初期化待機中（60秒）..."
    sleep 60
    echo "✅ 初期化完了"
    echo ""
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8100/eval | jq '{summary: .summary, cases: [.cases[] | {id, gr_ok, lr_ok}]}'
    ;;

  medium)
    echo "📊 中規模版（8個）でテスト開始..."
    $DOCKER_CMD compose down -v
    DATA_FILE=data/docs-light.jsonl $DOCKER_CMD compose up --detach
    echo "⏳ 初期化待機中（60秒）..."
    sleep 60
    echo "✅ 初期化完了"
    echo ""
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8100/eval | jq '{summary: .summary, cases: [.cases[] | {id, gr_ok, lr_ok}]}'
    ;;

  large)
    echo "📊 大規模版（50個）でテスト開始..."
    $DOCKER_CMD compose down -v
    DATA_FILE=data/docs-50.jsonl $DOCKER_CMD compose up --detach
    echo "⏳ 初期化待機中（90秒）..."
    sleep 90
    echo "✅ 初期化完了"
    echo ""
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8100/eval | jq '{summary: .summary, cases: [.cases[] | {id, gr_ok, lr_ok}]}'
    ;;

  compare)
    echo "📊 小規模版と大規模版を比較テスト開始..."
    echo ""

    echo "=== 小規模版（5個） ==="
    $DOCKER_CMD compose down -v
    DATA_FILE=data/docs.jsonl $DOCKER_CMD compose up --detach
    echo "⏳ 初期化待機中（60秒）..."
    sleep 60
    SMALL_GR=$(curl -s http://127.0.0.1:8100/eval | jq '.summary.graphrag_ok')
    SMALL_LR=$(curl -s http://127.0.0.1:8100/eval | jq '.summary.lightrag_ok')
    echo "✅ 小規模版: GraphRAG=$SMALL_GR/5, LightRAG=$SMALL_LR/5"
    echo ""

    echo "=== 大規模版（50個） ==="
    $DOCKER_CMD compose down -v
    DATA_FILE=data/docs-50.jsonl $DOCKER_CMD compose up --detach
    echo "⏳ 初期化待機中（90秒）..."
    sleep 90
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
    echo "  $0 small     # 小規模版（5個）でテスト"
    echo "  $0 medium    # 中規模版（8個）でテスト"
    echo "  $0 large     # 大規模版（50個）でテスト"
    echo "  $0 compare   # 小規模と大規模を比較"
    exit 1
    ;;
esac

