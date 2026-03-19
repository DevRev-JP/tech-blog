"""
agent_e2e.py
CustomerSupportAgent（エンドツーエンド）

ch8「AI AgentとKG」の統合実装例。
1回のサポートリクエスト処理の中でRead・Reason・Writeの3パターンをすべて使う。
- Read:  KGから顧客コンテキストを取得
- Reason: エスカレーション要否をKGで推論
- Write: 対応履歴をKGに記録

参照: books/knowledge-graph-llm-guide/kg-and-ai-agents.md
"""

import json
import os

from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from neo4j import GraphDatabase

# .envを読み込む
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

assert NEO4J_PASSWORD, "NEO4J_PASSWORD環境変数を設定してください（.envファイル推奨）"


class AgentMemorySystem:
    """Short-term / Long-term メモリを管理するクラス（簡略版）"""

    def __init__(self, driver, redis_client=None):
        self.driver = driver
        self.redis = redis_client  # 省略時はNone（Short-termは無効化）

    def persist_important_memory(self, user_id: str, memory: dict):
        """Long-term: 重要な情報をKGに永続化"""
        query = """
        MATCH (u:Customer {id: $user_id})
        CREATE (m:Memory {
            id: randomUUID(),
            content: $content,
            category: $category,
            importance: $importance,
            created_at: datetime()
        })
        CREATE (u)-[:HAS_MEMORY]->(m)
        """
        with self.driver.session() as session:
            session.run(
                query,
                user_id=user_id,
                content=memory["content"],
                category=memory.get("category", "general"),
                importance=memory.get("importance", 0.5)
            )


class CustomerSupportAgent:
    """KGを活用したカスタマーサポートAgent（エンドツーエンド）"""

    def __init__(self, driver):
        self.driver = driver
        self.llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)
        self.memory = AgentMemorySystem(driver, redis_client=None)  # 簡略化

    # クラウドLLMを使う場合（オプション）
    # from langchain_anthropic import ChatAnthropic
    # self.llm = ChatAnthropic(model="claude-sonnet-4-6")

    def handle_support_request(self, customer_id: str, message: str) -> dict:
        """サポートリクエストをエンドツーエンドで処理"""

        # Step 1: Read - KGから顧客コンテキストを取得
        customer_ctx = self._get_customer_context(customer_id)
        if not customer_ctx:
            return {"status": "error", "message": "顧客情報が見つかりません"}

        # Step 2: Reason - エスカレーション判断
        escalation = self._evaluate_escalation(customer_id, message)

        # Step 3: LLMで回答を生成
        system_prompt = self._build_system_prompt(customer_ctx, escalation)
        prompt = f"{system_prompt}\n\nユーザーの問い合わせ: {message}"
        reply = self.llm.invoke(prompt)

        # Step 4: Write - 対応履歴をKGに記録
        self._record_interaction(customer_id, message, reply, escalation)

        return {
            "status": "success",
            "reply": reply,
            "escalated": escalation["should_escalate"],
            "escalation_reason": escalation.get("reason", ""),
            "assigned_team": customer_ctx.get("team_name")
        }

    def _get_customer_context(self, customer_id: str) -> dict:
        """KGから顧客の全コンテキストを取得（Read）"""
        query = """
        MATCH (c:Customer {id: $id})
        OPTIONAL MATCH (c)-[:HAS_PLAN]->(plan:Plan)
        OPTIONAL MATCH (plan)-[:SUPPORTED_BY]->(team:SupportTeam)
        OPTIONAL MATCH (c)-[:SUBMITTED]->(recent_ticket:Ticket)
        WHERE recent_ticket.created_at > datetime() - duration('P30D')
        RETURN
            c.name AS customer_name,
            plan.name AS plan_name,
            plan.tier AS tier,
            team.name AS team_name,
            team.sla_hours AS sla_hours,
            count(DISTINCT recent_ticket) AS recent_tickets_count
        """
        with self.driver.session() as session:
            result = session.run(query, id=customer_id)
            record = result.single()
            return dict(record) if record else None

    def _evaluate_escalation(self, customer_id: str, message: str) -> dict:
        """エスカレーション要否をKGで推論（Reason）"""
        query = """
        MATCH (c:Customer {id: $customer_id})
        MATCH (c)-[:HAS_PLAN]->(plan:Plan)
        OPTIONAL MATCH (c)-[:SUBMITTED]->(t:Ticket)
        WHERE t.created_at > datetime() - duration('PT48H')
        WITH plan, count(t) AS ticket_count
        RETURN
            plan.tier = 'enterprise' AS is_enterprise,
            ticket_count AS recent_ticket_count,
            (plan.tier = 'enterprise' OR ticket_count >= 3) AS should_escalate
        """
        with self.driver.session() as session:
            result = session.run(query, customer_id=customer_id)
            record = result.single()

            if not record:
                return {"should_escalate": False, "reason": ""}

            reasons = []
            if record["is_enterprise"]:
                reasons.append("Enterpriseプラン")
            if record["recent_ticket_count"] >= 3:
                reasons.append(f"直近48時間で{record['recent_ticket_count']}件")

            return {
                "should_escalate": record["should_escalate"],
                "reason": "・".join(reasons)
            }

    def _build_system_prompt(self, ctx: dict, escalation: dict) -> str:
        escalation_note = ""
        if escalation["should_escalate"]:
            escalation_note = f"\n- エスカレーション対象: {escalation['reason']}"
        return f"""あなたは{ctx.get('team_name', 'サポート')}チームのエージェントです。

顧客情報:
- 名前: {ctx.get('customer_name')}
- プラン: {ctx.get('plan_name')} ({ctx.get('tier')})
- SLA: {ctx.get('sla_hours')}時間以内に解決
- 直近30日のチケット数: {ctx.get('recent_tickets_count')}件{escalation_note}

丁寧かつ簡潔に回答してください。"""

    def _record_interaction(self, customer_id: str, message: str,
                             reply: str, escalation: dict):
        """対応履歴をKGに記録（Write）"""
        query = """
        MATCH (c:Customer {id: $customer_id})
        CREATE (t:Ticket {
            id: randomUUID(),
            message: $message,
            reply: $reply,
            escalated: $escalated,
            created_at: datetime()
        })
        CREATE (c)-[:SUBMITTED]->(t)
        """
        with self.driver.session() as session:
            session.run(
                query,
                customer_id=customer_id,
                message=message[:500],
                reply=reply[:1000],
                escalated=escalation["should_escalate"]
            )


if __name__ == "__main__":
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        agent = CustomerSupportAgent(driver)

        # サンプル：Enterpriseプランの顧客（エスカレーション対象）
        result = agent.handle_support_request(
            customer_id="cust-001",
            message="APIの認証エラーが頻発しています。本番環境で影響が出ており、売上集計ができない状態です。"
        )

        print("エンドツーエンド処理結果:")
        print(f"  ステータス: {result['status']}")
        print(f"  担当チーム: {result.get('assigned_team')}")
        print(f"  エスカレーション: {result.get('escalated')} ({result.get('escalation_reason', '')})")
        print(f"  回答:\n{result.get('reply')}")
    finally:
        driver.close()
