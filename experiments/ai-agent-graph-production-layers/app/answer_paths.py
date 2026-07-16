"""Q1〜Q8 をファイル / Neo4j単体 / 層分離で答える."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.layers.audit_graph import q5_p0_top_products
from app.layers.context_graph import q8_context_nodes
from app.layers.graph import q1_customer, q3_blocked_services, q4_can_read
from app.layers.identity_graph import q6_same_customer
from app.layers.temporal_graph import q7_events_before_escalation, q7_escalated_at
from app.layers.vector import q2_similar
from app.shared import DATA_DIR, ISSUE_ID, load_json, neo4j_session

Precision = Literal["high", "medium", "low", "none"]

SIMILAR_QUERY = "Acme Search latency Globex"
CHANNEL_IDS = ["slack-globex-support", "email-globex-ops"]


@dataclass
class AnswerResult:
    value: Any
    precision: Precision
    reason: str


@dataclass(frozen=True)
class QuestionMeta:
    """1つの問いのメタデータ。質問文と効くグラフの種類を1箇所で持つ."""

    text: str
    graph_kind: str


QUESTION_META: dict[str, QuestionMeta] = {
    "Q1": QuestionMeta("このチケット（INC-001）の顧客は？", "[1]ナレッジグラフ"),
    "Q2": QuestionMeta("Slack とメールは同一顧客か？", "同一性グラフ（[1]KG の特殊化）"),
    "Q3": QuestionMeta("agent_guest は INC-001 を見てよいか？", "権限グラフ（[1]KG の特殊化）"),
    "Q4": QuestionMeta("ログ基盤障害の影響範囲は？", "依存関係グラフ（[1]KG の特殊化）"),
    "Q5": QuestionMeta("類似の過去障害は？", "コンテキスト（意味的類似・5種の外）"),
    "Q6": QuestionMeta("過去30日の P0 件数トップ製品は？", "監査グラフ（集計）"),
    "Q7": QuestionMeta("P0 昇格の30分前に何があったか？", "時間軸グラフ"),
    "Q8": QuestionMeta("このターンで LLM に渡すノードは？", "コンテキストグラフ"),
}

QUESTIONS: dict[str, str] = {qid: m.text for qid, m in QUESTION_META.items()}


def _neo4j_keyword_incidents(keyword: str) -> list[str]:
    cypher = """
    MATCH (i:Issue)
    WHERE toLower(i.title) CONTAINS toLower($kw)
       OR i.id = $issue_id
    RETURN DISTINCT i.id AS id
    ORDER BY id
    """
    with neo4j_session() as session:
        rows = session.run(cypher, kw=keyword, issue_id=ISSUE_ID)
        return [r["id"] for r in rows]


def _neo4j_p0_count_by_product() -> list[dict]:
    cypher = """
    MATCH (i:Issue)-[:AFFECTS]->(p:Product)
    WHERE i.severity = 'P0'
    RETURN p.name AS product, count(i) AS p0_count
    ORDER BY p0_count DESC
    """
    with neo4j_session() as session:
        rows = session.run(cypher)
        return [{"product": r["product"], "p0_count": r["p0_count"]} for r in rows]


# --- ファイル（断片） ---


def answer_file(qid: str) -> AnswerResult:
    frags = load_json(DATA_DIR / "fragments.json")
    texts = {f["source"]: f["text"] for f in frags}

    if qid == "Q1":
        return AnswerResult(
            value={
                "jira": "Globex Corp（明示）",
                "slack": "顧客名なし + INC-099 言及",
                "email": "製品のみ",
            },
            precision="low",
            reason="断片ごとに粒度が違う。Customer ノード / OWNED_BY Edge がない",
        )
    if qid == "Q2":
        return AnswerResult(
            value={"slack": "globex-support", "email": "ops@globex.example"},
            precision="low",
            reason="SAME_AS がない。別チャネル＝別顧客と誤認しやすい",
        )
    if qid == "Q3":
        return AnswerResult(
            value="プロンプトで「秘匿を答えるな」と書く想定",
            precision="none",
            reason="CAN_READ 型がない。断片に混ざれば漏れる",
        )
    if qid == "Q4":
        return AnswerResult(
            value=texts.get("runbook", ""),
            precision="medium",
            reason="叙述はあるが BLOCKS Edge として機械は辿れない",
        )
    if qid == "Q5":
        hits = [t for t in texts.values() if "Acme" in t or "検索" in t or "Search" in t]
        return AnswerResult(
            value=hits,
            precision="low",
            reason="キーワード一致のみ。意味的類似・ランキングなし",
        )
    if qid == "Q6":
        return AnswerResult(
            value=texts.get("note", ""),
            precision="none",
            reason="GROUP BY 不可。根拠ない叙述のみ",
        )
    if qid == "Q7":
        return AnswerResult(
            value="断片に時系列 Edge なし",
            precision="none",
            reason="昇格時刻・30分前のイベント鎖を型として持てない",
        )
    if qid == "Q8":
        return AnswerResult(
            value=list(texts.keys()),
            precision="low",
            reason="毎回渡す断片セットがブレる。スコープ固定なし",
        )
    raise KeyError(qid)


# --- Neo4j 単体 ---


def answer_neo4j_only(qid: str) -> AnswerResult:
    if qid == "Q1":
        v = q1_customer()
        return AnswerResult(v, "high", "KG traversal（AFFECTS→OWNED_BY）")
    if qid == "Q2":
        v = q6_same_customer(CHANNEL_IDS)
        return AnswerResult(v, "high", "SAME_AS traversal")
    if qid == "Q3":
        allowed = q4_can_read("agent_guest", ISSUE_ID)
        return AnswerResult(
            value=allowed,
            precision="high",
            reason="CAN_READ traversal（取得段階で遮断）",
        )
    if qid == "Q4":
        return AnswerResult(
            value=q3_blocked_services(),
            precision="high",
            reason="BLOCKS traversal は Graph DB 向き",
        )
    if qid == "Q5":
        ids = _neo4j_keyword_incidents("search")
        return AnswerResult(
            value=ids,
            precision="low",
            reason="Neo4j にベクトル層なし。タイトルキーワード一致のみ（過去障害を取りこぼす）",
        )
    if qid == "Q6":
        neo = _neo4j_p0_count_by_product()
        sql = q5_p0_top_products()
        return AnswerResult(
            value={"neo4j_issue_severity": neo, "sqlite_audit_log": sql},
            precision="low",
            reason="監査集計を Cypher に押し込むと Issue.severity 固定値だけになり audit_log と乖離",
        )
    if qid == "Q7":
        events = q7_events_before_escalation()
        return AnswerResult(
            value={
                "escalated_at": q7_escalated_at(),
                "within_30min_before": events,
            },
            precision="high",
            reason="Event 鎖は Neo4j で足りる（専用 TS DB は PoC では省略）",
        )
    if qid == "Q8":
        nodes = q8_context_nodes()
        ids = [n["node_id"] for n in nodes if n.get("node_id")]
        return AnswerResult(
            value=sorted(set(ids)),
            precision="high",
            reason="SCOPE_INCLUDES で node_ids を取得（層分離と同じ範囲）",
        )
    raise KeyError(qid)


# --- 層分離 ---


def answer_routed(qid: str) -> AnswerResult:
    if qid == "Q1":
        return AnswerResult(q1_customer(), "high", "Neo4j KG")
    if qid == "Q2":
        v = q6_same_customer(CHANNEL_IDS)
        return AnswerResult(v, "high", "Neo4j SAME_AS")
    if qid == "Q3":
        return AnswerResult(q4_can_read("agent_guest", ISSUE_ID), "high", "Neo4j CAN_READ")
    if qid == "Q4":
        return AnswerResult(q3_blocked_services(), "high", "Neo4j BLOCKS")
    if qid == "Q5":
        hits = q2_similar(SIMILAR_QUERY)
        return AnswerResult(
            value=[h.get("id") for h in hits],
            precision="high",
            reason="Qdrant 意味的類似（Embeddings 層）",
        )
    if qid == "Q6":
        return AnswerResult(q5_p0_top_products(), "high", "SQLite audit_log 集計")
    if qid == "Q7":
        events = q7_events_before_escalation()
        return AnswerResult(
            value={
                "escalated_at": q7_escalated_at(),
                "within_30min_before": events,
            },
            precision="high",
            reason="Neo4j Event + BEFORE（時間軸は宣言的 seed）",
        )
    if qid == "Q8":
        nodes = q8_context_nodes()
        ids = [n["node_id"] for n in nodes if n.get("node_id")]
        return AnswerResult(
            value=sorted(set(ids)),
            precision="high",
            reason="コンテキストスコープで node_ids 固定",
        )
    raise KeyError(qid)


def precision_label(p: Precision) -> str:
    return {"high": "◎ 確定", "medium": "△ 一部可", "low": "▲ 推測", "none": "✗ 不可"}[p]
