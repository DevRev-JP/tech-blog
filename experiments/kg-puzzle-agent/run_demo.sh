#!/usr/bin/env bash
# kg-puzzle-agent デモ入口 — Neo4j: Podman / Ollama: ホストのみ（compose に Ollama なし）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

COMPOSE="podman compose"
PYTHON="${PYTHON:-python3}"

usage() {
  cat <<'EOF'
Usage: ./run_demo.sh <command>

Commands:
  setup    Neo4j 起動 + ホスト Ollama 確認 + モデル pull
  compare  Part0: Skill 断片 vs コンテキストグラフ（A/B）
  part1    Part1: シード + 権限 + LangGraph エージェント
  part2    Part2: DB リセット + Graphiti ingest/search/history
  all      compare → part1 → part2

前提:
  cp env.sample .env
  pip install -r requirements.txt
  ollama serve  （ホスト、Metal/GPU 利用）
  LLM は gemma2:2b 固定（README 参照）
注意: 他 experiment（7474/7687）と Neo4j ポート競合不可
      11434 はホスト Ollama と共有（コンテナ版 Ollama は使わない）
EOF
}

ensure_env() {
  if [[ ! -f .env ]]; then
    cp env.sample .env
    echo "Created .env from env.sample"
  fi
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
}

wait_neo4j() {
  echo "Neo4j の準備を待っています（最大90秒）…"
  for _ in $(seq 1 18); do
    if curl -sf http://localhost:7474 >/dev/null 2>&1; then
      echo "Neo4j の準備ができました。"
      return 0
    fi
    sleep 5
  done
  echo "Neo4j が起動しません。podman compose ps で確認してください。" >&2
  exit 1
}

ensure_host_ollama() {
  local base="${OLLAMA_BASE_URL:-http://localhost:11434}"

  # コンテナ内 Ollama（他 experiment の kg-ollama 等）を拒否
  if [[ "${base}" =~ ^https?://(ollama|kg-ollama|kg-puzzle-ollama)(:|/|$) ]]; then
    echo "エラー: OLLAMA_BASE_URL はホスト向け (http://localhost:11434) にしてください。" >&2
    echo "  この experiment は Ollama コンテナを使いません。" >&2
    exit 1
  fi

  if command -v podman >/dev/null 2>&1; then
    local ollama_containers
    ollama_containers="$(podman ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep '11434' || true)"
    if [[ -n "${ollama_containers}" ]]; then
      echo "エラー: 11434 を Podman コンテナが使用中です。ホスト ollama serve のみ利用してください。" >&2
      echo "${ollama_containers}" >&2
      echo "  例: podman stop kg-ollama kg-learn-ollama-1" >&2
      exit 1
    fi
  fi

  if ! curl -sf "${base}/api/tags" >/dev/null 2>&1; then
    echo "ホスト Ollama に接続できません: ${base}" >&2
    echo "  ollama serve を起動してください（Mac では Metal/GPU が使えます）。" >&2
    echo "  他 experiment の Ollama コンテナは 11434 を奪うため停止してください。" >&2
    exit 1
  fi
  echo "ホスト Ollama OK: ${base}"
}

print_llm_model() {
  echo "LLM: ${OLLAMA_LLM_MODEL:-gemma2:2b}（.env の OLLAMA_LLM_MODEL。gemma2:2b 推奨）"
}

pull_ollama_models() {
  if ! command -v ollama >/dev/null 2>&1; then
    echo "警告: ollama CLI がありません。モデルは手動で pull してください。" >&2
    return 0
  fi
  ollama pull "${OLLAMA_LLM_MODEL:-gemma2:2b}"
  ollama pull "${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}"
}

cmd_setup() {
  ensure_env
  echo "[Step 1/4] ホスト Ollama 確認…"
  ensure_host_ollama
  echo "[Step 2/4] Podman Compose（Neo4j のみ）起動…"
  $COMPOSE up -d
  wait_neo4j
  echo "[Step 3/4] Ollama モデル pull（初回のみ）…"
  print_llm_model
  pull_ollama_models
  echo "[Step 4/4] Python 依存"
  echo "  pip install -r requirements.txt"
  echo "セットアップ完了。次: ./run_demo.sh compare"
}

cmd_part1() {
  ensure_env
  ensure_host_ollama
  echo "[Step 1/4] Project Alpha グラフ投入…"
  $PYTHON app/seed_static.py
  echo "[Step 2/4] Part0 compare（Skill vs グラフ）…"
  $PYTHON app/demo_skills_only.py
  echo "[Step 3/4] 権限デモ…"
  $PYTHON app/demo_permissions.py
  echo "[Step 4/4] LangGraph エージェント…"
  $PYTHON app/agent_langgraph.py
}

cmd_compare() {
  ensure_env
  ensure_host_ollama
  $PYTHON app/seed_static.py
  $PYTHON app/demo_skills_only.py
}

cmd_part2() {
  ensure_env
  ensure_host_ollama
  print_llm_model
  echo "Part1 の Project Alpha グラフと Graphiti のノードが混ざると混乱するため、Neo4j を空にします。"
  $COMPOSE down -v
  $COMPOSE up -d
  wait_neo4j
  echo "[Step 1/4] Graphiti 初期化…"
  $PYTHON app/graphiti_setup.py
  echo "[Step 2/4] エピソード取込 + 時系列 SSOT 適用（ホスト Ollama、数分）…"
  $PYTHON app/demo_temporal.py ingest
  echo "[Step 3/4] search（現在有効ファクト + 根拠）…"
  $PYTHON app/demo_temporal.py search
  echo "[Step 4/4] history（予算変遷）…"
  $PYTHON app/demo_temporal.py history
}

case "${1:-}" in
  setup) cmd_setup ;;
  compare) cmd_compare ;;
  part1) cmd_part1 ;;
  part2) cmd_part2 ;;
  all)
    cmd_setup
    cmd_compare
    cmd_part1
    cmd_part2
    ;;
  -h|--help|"") usage ;;
  *) echo "Unknown command: $1"; usage; exit 1 ;;
esac
