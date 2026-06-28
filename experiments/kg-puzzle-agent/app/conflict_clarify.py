"""Part0 Q3: グラフ上の現行 fact と新規断片の矛盾検出 → 人への確認質問.

矛盾検出は正規表現ヒューリスティック（本番の ingest/スキーマ検証ではない）。
聞き返しはテンプレ + LLM 1 プロンプト（LangGraph 分岐なし）。README #demo-vs-production。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared import (
    DATA_DIR,
    checkpoint,
    demo_run_context,
    get_llm,
    get_neo4j_driver,
    is_demo_batch,
    is_demo_quiet,
    milestone,
    section,
)


def get_canonical_owner(driver, project_name: str = "Alpha") -> str | None:
    with driver.session() as session:
        row = session.run(
            """
            MATCH (p:Project {name: $name})-[:OWNED_BY]->(t:Team)
            RETURN t.name AS team
            """,
            name=project_name,
        ).single()
        return row["team"] if row else None


def _incoming_owner_claims(fragments: list[dict]) -> list[dict]:
    """断片テキストから主担当チームの主張を抽出（デモ用ヒューリスティック）."""
    claims: list[dict] = []
    pattern = re.compile(r"(?:チーム|Team)\s*([AB])", re.I)
    for frag in fragments:
        text = frag.get("text", "")
        for match in pattern.finditer(text):
            team = f"Team {match.group(1).upper()}"
            role = "主担当" if "主担当" in text else "言及"
            claims.append(
                {
                    "team": team,
                    "role": role,
                    "label": frag.get("label", frag.get("source", "?")),
                    "text": text,
                }
            )
    return claims


def detect_owner_conflict(canonical: str | None, fragments: list[dict]) -> dict | None:
    if not canonical:
        return None
    conflicting = [c for c in _incoming_owner_claims(fragments) if c["team"] != canonical]
    if not conflicting:
        return None
    primary = next((c for c in conflicting if c["role"] == "主担当"), conflicting[0])
    return {
        "canonical": canonical,
        "incoming": primary,
        "all_incoming": conflicting,
    }


def build_clarification_question(conflict: dict) -> str:
    inc = conflict["incoming"]
    canonical = conflict["canonical"]
    return (
        f"正式な担当は {canonical} です（グラフの OWNED_BY）。"
        f"一方、{inc['label']} では「{inc['text']}」とあります。"
        f"**現行の正はどちらですか？** 古いドラフトを失効させますか？"
    )


def ask_clarification_with_llm(conflict: dict, user_question: str) -> str:
    """矛盾検出後、LLM にチャット調の聞き返しだけさせる（確定回答は禁止）."""
    inc = conflict["incoming"]
    llm = get_llm()
    prompt = f"""あなたはチーム向け AI アシスタントです。ユーザーの質問に **まだ答えない** でください。
ナレッジグラフ上の現行 fact と、新しく取り込んだ断片が矛盾しています。
利用者に **確認の質問だけ** を日本語で返してください（1〜3文、丁寧なチャット調）。

## グラフ（現行・確定）
Project Alpha -[:OWNED_BY]-> {conflict['canonical']}

## 新規断片（矛盾）
[{inc['label']}] {inc['text']}

## ユーザーの質問
{user_question}

## ルール
- Team A / Team B どちらかを断定しない
- グラフの {conflict['canonical']} と断片の {inc['team'] if 'team' in inc else '異なるチーム'} の **両方** に触れる
- 「どちらが正ですか」「古いドラフトを失効させますか」等、人間の判断を仰ぐ
- 回答（結論）ではなく確認質問のみ
"""
    return llm.invoke(prompt).content.strip()


def run_conflict_clarify_demo(data: dict) -> None:
    trap = data.get("trap_question") or {}
    fragments = trap.get("fragments") or []
    if not fragments:
        return

    driver = get_neo4j_driver()
    try:
        canonical = get_canonical_owner(driver)
    finally:
        driver.close()

    conflict = detect_owner_conflict(canonical, fragments)
    if not conflict:
        if not is_demo_batch():
            section("Q3: 矛盾検出 — スキップ")
            print("（主担当の矛盾断片が検出されませんでした）")
        return

    if is_demo_batch() and is_demo_quiet():
        milestone("Q3: グラフ vs 新規断片の矛盾 → 確認質問（Skill は Q2 で黙って確定）")
        return

    section("Q3: 矛盾検出 — 推測で決めず人に確認する（KG）")
    print(
        "（検出: 正規表現による PoC 簡略実装 — 本番は ingest/スキーマ検証。"
        " README #demo-vs-production）"
    )
    print(f"グラフ（現行）: Project Alpha -[:OWNED_BY]-> {conflict['canonical']}")
    inc = conflict["incoming"]
    print(f"新規断片: [{inc['label']}] {inc['text']}")
    question = trap.get("question", "プロジェクトAlphaの担当チームはどれ？")
    print(f"ユーザー質問（チャット想定）: {question}")
    print()
    section("確認テンプレート（決定論 · 再現用）")
    print(build_clarification_question(conflict))
    print()
    section("LLM がチャットで聞き返す（確定回答なし）")
    try:
        chat_reply = ask_clarification_with_llm(conflict, question)
        print(chat_reply)
    except Exception as exc:  # noqa: BLE001 — デモは Ollama 未起動でもテンプレートで完走
        print(f"（Ollama 聞き返しをスキップ: {exc}）")
    print()
    print(
        "→ Q2 の断片直渡し（A）は断片を推測で統合し、Team B と断定しがち。"
        " KG 経路では確定回答の前に **差分を見せて聞き返す**（Slack UI・LangGraph 分岐は未実装）。"
    )


def main() -> None:
    with demo_run_context():
        data = json.loads((DATA_DIR / "tool_fragments.json").read_text(encoding="utf-8"))
        run_conflict_clarify_demo(data)
        checkpoint(
            "Part0 Q3（矛盾 → 確認）",
            [
                "グラフ OWNED_BY（Team A）と Jira 古ドラフト（Team B）の差が表示される",
                "確認テンプレートに「現行の正はどちらですか？」が含まれる",
                "LLM 聞き返し: Team A/B を断定せず確認質問のみ（Ollama 要）",
                "Q2 Skill（A）との対比: 断片だけでは黙って確定しがち",
            ],
        )


if __name__ == "__main__":
    main()
