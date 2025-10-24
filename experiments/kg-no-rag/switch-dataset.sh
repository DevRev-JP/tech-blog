#!/bin/bash

# データセット切り替えスクリプト
# 使い方:
#   ./switch-dataset.sh small   # 小規模版（5個）
#   ./switch-dataset.sh large   # 大規模版（50個）
#   ./switch-dataset.sh compare # 両方実行して結果を比較

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

case "${1:-small}" in
  small)
    echo "📊 小規模版（5個）でテスト開始..."
    docker compose down -v
    docker compose up --detach
    echo "⏳ 初期化待機中（60秒）..."
    sleep 60
    echo "✅ 初期化完了"
    echo ""
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8000/eval | jq '{summary: .summary, cases: [.cases[] | {id, rag_ok, kg_ok}]}'
    ;;

  large)
    echo "📊 大規模版（50個）でテスト開始..."
    docker compose down -v
    DOCS_FILE=docs-50.jsonl docker compose up --detach
    echo "⏳ 初期化待機中（60秒）..."
    sleep 60
    echo "✅ 初期化完了"
    echo ""
    echo "📈 テスト結果:"
    curl -s http://127.0.0.1:8000/eval | jq '{summary: .summary, cases: [.cases[] | {id, rag_ok, kg_ok}]}'
    ;;

  compare)
    echo "📊 両バージョンを比較テスト開始..."
    echo ""

    echo "=== 小規模版（5個） ==="
    docker compose down -v
    docker compose up --detach
    echo "⏳ 初期化待機中（60秒）..."
    sleep 60
    SMALL_KG=$(curl -s http://127.0.0.1:8000/eval | jq '.summary.kg_correct')
    SMALL_RAG=$(curl -s http://127.0.0.1:8000/eval | jq '.summary.rag_correct')
    echo "✅ 小規模版: KG=$SMALL_KG/5, RAG=$SMALL_RAG/5"
    echo ""

    echo "=== 大規模版（50個） ==="
    docker compose down -v
    DOCS_FILE=docs-50.jsonl docker compose up --detach
    echo "⏳ 初期化待機中（60秒）..."
    sleep 60
    LARGE_KG=$(curl -s http://127.0.0.1:8000/eval | jq '.summary.kg_correct')
    LARGE_RAG=$(curl -s http://127.0.0.1:8000/eval | jq '.summary.rag_correct')
    echo "✅ 大規模版: KG=$LARGE_KG/5, RAG=$LARGE_RAG/5"
    echo ""

    echo "📊 結果比較:"
    echo "┌─────────┬─────┬─────┐"
    echo "│ バージョン │ KG  │ RAG │"
    echo "├─────────┼─────┼─────┤"
    echo "│ 小規模(5個) │ $SMALL_KG/5 │ $SMALL_RAG/5 │"
    echo "│ 大規模(50個)│ $LARGE_KG/5 │ $LARGE_RAG/5 │"
    echo "└─────────┴─────┴─────┘"
    ;;

  *)
    echo "使い方:"
    echo "  $0 small     # 小規模版（5個）でテスト"
    echo "  $0 large     # 大規模版（50個）でテスト"
    echo "  $0 compare   # 両方実行して比較"
    exit 1
    ;;
esac
