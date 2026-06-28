#!/usr/bin/env bash
# kg-puzzle-agent デモ入口 — Neo4j: Docker/Podman / Ollama: ホストのみ（compose に Ollama なし）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Podman compose: 警告のみ抑制（PROVIDER=podman は Mac で up -d が壊れるため使わない）
export PODMAN_COMPOSE_WARNING_LOGS="${PODMAN_COMPOSE_WARNING_LOGS:-0}"

# Docker か Podman か自動選択（COMPOSE 環境変数で上書き可）
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
DEMO_VERBOSE="${DEMO_VERBOSE:-0}"
_DEMO_PREFLIGHT_DONE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--verbose)
      DEMO_VERBOSE=1
      shift
      ;;
    -q|--quiet)
      shift
      ;;
    *)
      break
      ;;
  esac
done
export DEMO_VERBOSE

run_python() {
  $PYTHON "$@"
}

demo_phase() {
  echo ""
  printf '━%.0s' {1..56}
  echo ""
  echo "  $1"
  if [[ -n "${2:-}" ]]; then
    echo "  $2"
  fi
  printf '━%.0s' {1..56}
  echo ""
}

demo_done() {
  echo ""
  printf '━%.0s' {1..56}
  echo ""
  echo "  デモ完了"
  printf '━%.0s' {1..56}
  echo ""
  echo "  Part0  グラフは根拠付き / 断片直渡しは矛盾に弱い / Q3 は確認質問へ"
  echo "  Part1  権限は取得段階で遮断（断片は漏れうる）"
  echo "  Part2  500万→800万 · as-of · 視点 · 未解決矛盾"
  echo ""
  echo "  Neo4j Browser: http://localhost:7474"
  echo "  詳細ログ: DEMO_VERBOSE=1 ./run_demo.sh part2"
  echo "  手順:     ./run_demo.sh guide"
  echo ""
}

usage() {
  cat <<'EOF'
Usage: ./run_demo.sh [--verbose|-v] <command>

Options:
  --verbose, -v  Graphiti/Neo4j の詳細ログを表示（DEMO_VERBOSE=1 と同じ。デフォルトは結果のみ）

Commands:
  setup          Neo4j 起動 + ホスト Ollama 確認 + モデル pull
  seed           Part0/1 用 Project Alpha グラフだけ投入
  compare        Part0: 断片直渡し vs グラフ（Q1 + Q2 現場混在 + Q3 矛盾→確認）
  clarify        Part0 Q3 のみ（グラフ vs 新規断片 → 確認質問）
  quick          Part0 + Part1 権限（約1〜2分、Part2 なし）
  part1          シード + compare + 権限漏洩 + LangGraph
  part2          DB リセット + Graphiti ingest + as-of / 視点 search + history
  part2-search   取込済み DB で search のみ（preset: monday|friday|today|sales|eng|manager）
  full           setup + part1 + part2（フル体験、十数分）
  guide          手作業で一つずつ確認する手順を表示

例:
  ./run_demo.sh quick
  ./run_demo.sh --verbose part2   # ingest 中の Graphiti ログも見る
  ./run_demo.sh guide
  ./run_demo.sh part2-search monday

前提:
  cp env.sample .env
  pip install -r requirements.txt  # venv は任意（.venv を作れば activate 不要で自動検出）
  ollama serve  （ホスト、Metal/GPU 利用）
EOF
}

cmd_guide() {
  cat <<'EOF'
=== 手作業ガイド（一つずつ確認） ===

0. 準備（初回のみ）
   ./run_demo.sh setup

--- Part0: 断片直渡し（Skill 相当） vs グラフ ---

1. グラフ投入
   ./run_demo.sh seed
   → Neo4j Browser で README の Part0 Cypher を実行

2. Q1 + Q2 + Q3 比較
   ./run_demo.sh compare
   → B に ## 参照したグラフ、Q2 で A=Team B / B=Team A
   → Q3: グラフ Team A vs Jira Team B → 確認質問テンプレート

   # Q3 のみ
   python app/conflict_clarify.py

--- Part1: 権限 + LangGraph ---

3. 権限・秘匿漏洩
   python app/demo_permissions.py
   → guest に Deal なし / 断片直渡しで 800万 / グラフ guest は遮断

4. LangGraph
   python app/agent_langgraph.py
   → グラフ参照 → 回答の 2 段

--- Part2: 時系列（十数分） ---

5. Neo4j リセット + Graphiti 初期化
   ./run_demo.sh part2   # 先頭で Neo4j リセット
   # または手動: ./run_demo.sh setup  （初回以降は不要）

6. as-of 切り替え（数秒ずつ）
   ./run_demo.sh part2-search monday    # 500万のみ
   ./run_demo.sh part2-search today     # 800万 + 10月予定 + 矛盾 + 議論用確認例
   ./run_demo.sh part2-search sales
   ./run_demo.sh part2-search eng
   python app/demo_temporal.py history

7. Neo4j で目視 — README の Part2 Cypher（valid_at / invalid_at）

詳細ログ（デバッグ時）:
  ./run_demo.sh --verbose part2
  または .env に DEMO_VERBOSE=1
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

compose() {
  if [[ "$DEMO_VERBOSE" == "1" ]]; then
    $COMPOSE "$@"
  else
    $COMPOSE "$@" >/dev/null
  fi
}

wait_neo4j() {
  if [[ "$DEMO_VERBOSE" == "1" ]]; then
    echo "Neo4j の準備を待っています（最大90秒）…"
  else
    printf "Neo4j 起動中"
  fi
  for _ in $(seq 1 18); do
    if curl -sf http://localhost:7474 >/dev/null 2>&1; then
      if [[ "$DEMO_VERBOSE" == "1" ]]; then
        echo "Neo4j の準備ができました。"
      else
        echo " … OK"
      fi
      return 0
    fi
    [[ "$DEMO_VERBOSE" != "1" ]] && printf "."
    sleep 5
  done
  echo ""
  echo "Neo4j が起動しません。${COMPOSE} ps で確認してください。" >&2
  exit 1
}

ensure_host_ollama() {
  local base="${OLLAMA_BASE_URL:-http://localhost:11434}"

  if [[ "${base}" =~ ^https?://(ollama|kg-ollama|kg-puzzle-ollama)(:|/|$) ]]; then
    echo "エラー: OLLAMA_BASE_URL はホスト向け (http://localhost:11434) にしてください。" >&2
    exit 1
  fi

  if ! curl -sf "${base}/api/tags" >/dev/null 2>&1; then
    echo "ホスト Ollama に接続できません: ${base}" >&2
    echo "  ollama serve を起動してください。" >&2
    exit 1
  fi
  if [[ "$DEMO_VERBOSE" == "1" ]]; then
    echo "ホスト Ollama OK: ${base}"
  fi
}

preflight() {
  [[ "$_DEMO_PREFLIGHT_DONE" == "1" ]] && return 0
  ensure_env
  ensure_host_ollama
  _DEMO_PREFLIGHT_DONE=1
}

print_llm_model() {
  if [[ "$DEMO_VERBOSE" == "1" ]]; then
    echo "LLM: ${OLLAMA_LLM_MODEL:-gemma2:2b}（.env の OLLAMA_LLM_MODEL）"
  fi
}

ollama_has_model() {
  local name="$1"
  ollama show "$name" >/dev/null 2>&1
}

pull_ollama_models() {
  if ! command -v ollama >/dev/null 2>&1; then
    echo "警告: ollama CLI がありません。モデルは手動で pull してください。" >&2
    return 0
  fi
  local llm="${OLLAMA_LLM_MODEL:-gemma2:2b}"
  local embed="${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}"
  if ollama_has_model "$llm" && ollama_has_model "$embed"; then
    if [[ "$DEMO_VERBOSE" == "1" ]]; then
      echo "  ✓ Ollama モデル済み: ${llm}, ${embed}"
    else
      echo "  ✓ Ollama モデル済み（${llm}, ${embed}）"
    fi
    return 0
  fi
  print_llm_model
  if ! ollama_has_model "$llm"; then
    ollama pull "$llm"
  fi
  if ! ollama_has_model "$embed"; then
    ollama pull "$embed"
  fi
}

cmd_setup() {
  preflight
  echo "[1/4] ホスト Ollama 確認"
  echo "[2/4] Neo4j 起動"
  compose up -d
  wait_neo4j
  echo "[3/4] Ollama モデル"
  pull_ollama_models
  echo "[4/4] Python 依存 — pip install -r requirements.txt"
  echo ""
  echo "セットアップ完了 → ./run_demo.sh quick  または  ./run_demo.sh full"
}

cmd_compare() {
  preflight
  run_python app/seed_static.py
  run_python app/demo_skills_only.py
}

cmd_clarify() {
  preflight
  run_python app/seed_static.py
  run_python app/conflict_clarify.py
}

cmd_seed() {
  preflight
  run_python app/seed_static.py
}

cmd_quick() {
  preflight
  demo_phase "quick" "Part0 + Part1 権限（Part2 なし、約1〜2分）"
  export DEMO_BATCH=1
  run_python app/seed_static.py
  run_python app/demo_skills_only.py
  run_python app/demo_permissions.py
  unset DEMO_BATCH
  echo ""
  echo "→ 深掘り: ./run_demo.sh part2  または  ./run_demo.sh full"
}

cmd_part1() {
  preflight
  export DEMO_BATCH=1
  demo_phase "Part0" "断片直渡し vs グラフ"
  run_python app/seed_static.py
  run_python app/demo_skills_only.py
  demo_phase "Part1" "権限 + LangGraph"
  run_python app/demo_permissions.py
  run_python app/agent_langgraph.py
  unset DEMO_BATCH
}

cmd_part2_search_only() {
  local preset="${1:-today}"
  local as_of=""
  local persona=""
  case "$preset" in
    monday) as_of="monday" ;;
    friday) as_of="friday" ;;
    today) as_of="today" ;;
    sales) as_of="today"; persona="sales" ;;
    eng) as_of="today"; persona="eng" ;;
    manager) as_of="today"; persona="manager" ;;
    *)
      echo "Unknown preset: $preset（monday|friday|today|sales|eng|manager）" >&2
      exit 1
      ;;
  esac
  preflight
  if [[ -n "$persona" ]]; then
    run_python app/demo_temporal.py search --as-of "$as_of" --persona "$persona"
  else
    run_python app/demo_temporal.py search --as-of "$as_of"
  fi
}

cmd_part2() {
  preflight
  export DEMO_BATCH=1
  print_llm_model
  if [[ "$DEMO_VERBOSE" != "1" ]]; then
    echo "Neo4j リセット（Part2 用 Graphiti DB）…"
  else
    echo "Part1 静的グラフと Graphiti が混ざるため Neo4j をリセットします。"
  fi
  compose down -v
  compose up -d
  wait_neo4j
  demo_phase "Part2" "Graphiti ingest + as-of search"
  run_python app/graphiti_setup.py
  run_python app/demo_temporal.py ingest
  run_python app/demo_temporal.py search --as-of monday
  run_python app/demo_temporal.py search --as-of today
  run_python app/demo_temporal.py search --as-of today --persona sales
  run_python app/demo_temporal.py search --as-of today --persona eng
  run_python app/demo_temporal.py history
  unset DEMO_BATCH
  echo ""
  echo "→ Part2 完了 · Neo4j Browser: http://localhost:7474"
}

cmd_all() {
  cmd_setup
  echo ""
  cmd_part1
  cmd_part2
  demo_done
}

case "${1:-}" in
  setup) cmd_setup ;;
  seed) cmd_seed ;;
  compare) cmd_compare ;;
  clarify) cmd_clarify ;;
  quick) cmd_quick ;;
  part1) cmd_part1 ;;
  part2) cmd_part2 ;;
  part2-search) cmd_part2_search_only "${2:-today}" ;;
  full|all) cmd_all ;;
  guide) cmd_guide ;;
  -h|--help|"") usage ;;
  *) echo "Unknown command: $1"; usage; exit 1 ;;
esac
