#!/usr/bin/env python3
"""実機検証ログ用の manifest.json を stdout に出力する."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.demo_agent import DEFAULT_QIDS  # noqa: E402
from app.shared import DEFAULT_LLM_MODEL, ollama_available  # noqa: E402


def _git_head() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT.parent.parent,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _ollama_models() -> list[str]:
    if not ollama_available():
        return []
    import urllib.request

    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode())
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except OSError:
        return []


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_id = (
        sys.argv[2]
        if len(sys.argv) > 2
        else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    manifest = {
        "tag": tag,
        "run_id": run_id,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "ai-agent-graph-production-layers",
        "issue_id": "INC-001",
        "agent_default_qids": DEFAULT_QIDS,
        "ollama_llm_model": os.getenv("OLLAMA_LLM_MODEL", DEFAULT_LLM_MODEL),
        "ollama_embed_model": "nomic-embed-text",
        "ollama_available": ollama_available(),
        "ollama_models_installed": _ollama_models(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_head": _git_head(),
        "commands": [
            "./run_demo.sh scenario",
            "./run_demo.sh compare",
            "./run_demo.sh agent",
        ],
        "goals": {
            "G1": "agent Q4/Q6/Q7 — MD vs グラフの LLM 回答差",
            "G2": "scenario S1-S5 — 第1部5種の別役割",
            "G3": "agent Q5 — Neo4j単体 vs 層分離（看板）",
        },
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
