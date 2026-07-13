#!/usr/bin/env bash
# ai-agent-graph-production-layers — 第3部ハンズオン（単体完結）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export PODMAN_COMPOSE_WARNING_LOGS="${PODMAN_COMPOSE_WARNING_LOGS:-0}"

if [[ -z "${COMPOSE:-}" ]]; then
  if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
  elif command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1; then
    COMPOSE="podman compose"
  else
    echo "エラー: docker compose または podman compose が必要です。" >&2
    exit 1
  fi
fi

PYTHON="${PYTHON:-$([ -f .venv/bin/python ] && echo '.venv/bin/python' || echo 'python3')}"

usage() {
  cat <<'EOF'
Usage: ./run_demo.sh <command>

Commands:
  setup     Neo4j + Qdrant 起動、seed 投入
  scenario  障害 INC-001 を第1部5種で辿る（G2・LLM 不要）
  agent     LangGraph + Ollama（AIがMDを読む vs グラフを読む・G1本丸）
  compare   8問の精度ラベル ◎/▲/✗ 一覧（LLM 不要・補助）
  graphs    第1部5種類の Edge 型表示（開発用）
  stage0    段階0: fragments.json の限界
  stage1    段階1: Neo4j 単体のつらさ
  stage2    段階2: Q1〜Q8 ルーティング（層の一覧）
  quick     compare の別名
  full      scenario + agent + compare（推奨通し）
  guide     体験の全体像

前提: ホスト Ollama（agent で LLM 回答を見る場合）
  ollama serve && ollama pull gemma2:2b
  ※ scenario / compare / graphs は Ollama なしでも可
EOF
}

wait_neo4j() {
  local i
  for i in $(seq 1 30); do
    if $PYTHON -c "from app.shared import neo4j_driver; neo4j_driver().verify_connectivity()" 2>/dev/null; then
      return 0
    fi
    sleep 2
  done
  echo "Neo4j の起動待ちがタイムアウトしました。" >&2
  exit 1
}

cmd_setup() {
  $COMPOSE -f compose.yaml up -d
  echo "Neo4j / Qdrant 起動待ち..."
  sleep 5
  wait_neo4j
  $PYTHON app/setup_seed.py
}

cmd_scenario() { $PYTHON app/demo_scenario.py; }
cmd_graphs() { $PYTHON app/demo_graphs.py; }
cmd_compare() { $PYTHON app/compare_layers.py; }
cmd_agent() { $PYTHON app/demo_agent.py; }
cmd_stage0() { $PYTHON app/stage0_fragments.py; }
cmd_stage1() { $PYTHON app/stage1_neo4j_only.py; }
cmd_stage2() { $PYTHON app/stage2_router.py; }

cmd_quick() {
  cmd_compare
}

cmd_full() {
  cmd_scenario
  cmd_agent
  cmd_compare
}

cmd_guide() {
  cat <<'EOF'

体験の全体像（単体完結 — 他 experiment 不要）

  setup    → Neo4j + Qdrant + SQLite seed
  scenario → 第1部5種を1本の障害物語で辿る（G2・LLM 不要）
  agent    → LangGraph + Ollama（MD vs グラフ・G1 本丸）
  compare  → 8問の精度ラベル ◎/▲/✗（補助・LLM 不要）
  graphs   → 第1部5種の Edge 型（開発用）
  stage2   → Q1〜Q8 ルーティング一覧
  quick    → compare と同じ
  full     → scenario + agent + compare

題材: 障害対応 INC-001 / Acme Search / Globex Corp

Neo4j Browser: http://localhost:7474
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    setup) cmd_setup ;;
    scenario) cmd_scenario ;;
    graphs) cmd_graphs ;;
    compare) cmd_compare ;;
    agent) cmd_agent ;;
    stage0) cmd_stage0 ;;
    stage1) cmd_stage1 ;;
    stage2) cmd_stage2 ;;
    quick) cmd_quick ;;
    full) cmd_full ;;
    guide) cmd_guide ;;
    -h|--help|help|"") usage ;;
    *) echo "不明なコマンド: $cmd" >&2; usage; exit 1 ;;
  esac
}

main "$@"
