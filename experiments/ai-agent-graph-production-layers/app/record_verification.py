#!/usr/bin/env python3
"""記事掲載用: scenario / compare / agent の実機ログを verification-logs/<tag>/runs/<run_id>/ に追記保存."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS_ROOT = ROOT / "verification-logs"
sys.path.insert(0, str(ROOT))

from app.answer_paths import (  # noqa: E402
    QUESTIONS,
    answer_file,
    answer_neo4j_only,
    answer_routed,
    precision_label,
)

COMPARE_IDS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]


def _run_id_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _run(cmd: list[str], log_path: Path, recorded_at: str) -> int:
    header = (
        f"# command: {' '.join(cmd)}\n"
        f"# recorded: {recorded_at}\n"
        f"# run_id: {log_path.parent.name}\n\n"
    )
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    body = proc.stdout
    if proc.stderr:
        body += "\n--- stderr ---\n" + proc.stderr
    log_path.write_text(header + body, encoding="utf-8")
    return proc.returncode


def _write_summary(out_dir: Path, manifest: dict) -> None:
    tag = manifest["tag"]
    run_id = manifest["run_id"]
    lines = [
        f"# 実機検証サマリー — {tag} / {run_id}",
        "",
        f"- 記録日時 (UTC): {manifest['recorded_at_utc']}",
        f"- LLM: `{manifest['ollama_llm_model']}` (temperature=0)",
        f"- agent 既定問い: {', '.join(manifest['agent_default_qids'])}",
        f"- git HEAD: `{manifest.get('git_head') or 'n/a'}`",
        "",
        "生ログ: 同ディレクトリの `scenario.log` / `compare.log` / `agent.log`",
        "",
        "## G2 — scenario（LLM 不要）",
        "",
        "| ステップ | 種 | 問い |",
        "|---------|-----|------|",
        "| S1 | [1] KG | INC-001 の顧客は？ |",
        "| S2 | [2] タスク | 調査の前提タスクは？ |",
        "| S3 | [3] DAG | 取得パイプラインの順は？ |",
        "| S4 | [4] WF | P0 承認・差し戻しは？ |",
        "| S5 | [5] ステート | 今どのフェーズ？ |",
        "",
        "## compare — 8問精度（LLM 不要）",
        "",
        "### A. ファイル vs グラフ（分離）",
        "",
        "| ID | 質問 | ファイル | グラフ(分離) |",
        "|----|------|---------|-------------|",
    ]
    for qid in COMPARE_IDS:
        f = answer_file(qid)
        r = answer_routed(qid)
        lines.append(
            f"| {qid} | {QUESTIONS[qid]} | {precision_label(f.precision)} | {precision_label(r.precision)} |"
        )

    lines.extend(
        [
            "",
            "### B. Neo4j単体 vs 分離（差が出る問いのみ）",
            "",
            "| ID | Neo4j単体 | 分離 | 記事での位置づけ |",
            "|----|-----------|------|----------------|",
        ]
    )
    for qid in COMPARE_IDS:
        neo = answer_neo4j_only(qid)
        routed = answer_routed(qid)
        if neo.precision == routed.precision and neo.value == routed.value:
            continue
        role = "看板（分離の理由）" if qid in ("Q2", "Q5") else "参考"
        if qid == "Q7":
            role = "分離不要（Neo4jで足りる）"
        lines.append(
            f"| {qid} | {precision_label(neo.precision)} | {precision_label(routed.precision)} | {role} |"
        )

    lines.extend(
        [
            "",
            "## G1 + G3 — agent（LLM 回答は agent.log 参照）",
            "",
            "| ID | ゴール | 期待する傾向 |",
            "|----|--------|-------------|",
            "| Q6 | G1 | MD=断定できない / グラフ=同一顧客と根拠つき回答 |",
            "| Q7 | G1 | MD=時系列不可 / グラフ=Event+BEFORE で列挙 |",
            "| Q5 | G3 | MD=断定できない / 分離=集計回答 / Neo4j単体=fact弱く断定できない |",
            "| Q4 | G1 | MD=チケット内容に触れる / グラフ=権限なしで遮断 |",
            "",
            "## 記事への転記メモ",
            "",
            "- **再現性が高い**: Q5 集計件数、Q2 の INC ID、compare の ◎/▲/✗ ラベル",
            "- **モデル依存**: agent の自然文（`gemma2:2b` 想定）。傾向が一致すれば OK",
            "- **再実行**: `./run_demo.sh verify` は既存ログを上書きせず、新しい `runs/<run_id>/` を追記する",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_id = _run_id_now()
    tag_dir = LOGS_ROOT / tag
    out_dir = tag_dir / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_proc = subprocess.run(
        [sys.executable, str(ROOT / "app" / "verification_manifest.py"), tag, run_id],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    manifest = json.loads(manifest_proc.stdout)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    recorded_at = manifest["recorded_at_utc"]
    py = sys.executable
    steps = [
        ([py, "app/demo_scenario.py"], "scenario.log"),
        ([py, "app/compare_layers.py"], "compare.log"),
        ([py, "app/demo_agent.py"], "agent.log"),
    ]
    failed: list[str] = []
    for cmd, log_name in steps:
        rc = _run(cmd, out_dir / log_name, recorded_at)
        if rc != 0:
            failed.append(log_name)

    _write_summary(out_dir, manifest)

    index_entry = {
        "tag": tag,
        "run_id": run_id,
        "recorded_at_utc": recorded_at,
        "path": f"{tag}/runs/{run_id}",
        "git_head": manifest.get("git_head"),
        "ollama_llm_model": manifest.get("ollama_llm_model"),
    }
    _append_jsonl(LOGS_ROOT / "index.jsonl", index_entry)
    _append_jsonl(tag_dir / "index.jsonl", index_entry)

    print(f"検証ログを追記しました: {out_dir}")
    print(f"  index: verification-logs/index.jsonl")
    for p in sorted(out_dir.iterdir()):
        print(f"  - {p.name}")
    if failed:
        print(f"警告: 終了コード非0: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
