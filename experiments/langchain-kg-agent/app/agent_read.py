"""
agent_read.py
パターン1：Read（KGから情報を取得してタスク実行）

ch8「AI AgentとKG」のReadパターン実装例。
SupportAgentWithKGがKGを参照専用の知識源として使い、
チケットを受け取り、KG情報をコンテキストに含めて回答を生成する。

参照: books/knowledge-graph-llm-guide/kg-and-ai-agents.md
"""

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


class SupportAgentWithKG:
    def __init__(self, neo4j_uri: str, neo4j_auth: tuple):
        self.llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)

    def get_routing_info(self, customer_id: str, issue_category: str) -> dict:
        """KGから担当者・優先度・関連ナレッジを取得（Read パターン）"""
        query = """
        MATCH (c:Customer {id: $customer_id})
        MATCH (c)-[:HAS_PLAN]->(plan:Plan)
        MATCH (plan)-[:SUPPORTED_BY]->(team:SupportTeam)
        RETURN
            team.name AS team_name,
            team.sla_hours AS sla_hours,
            plan.tier AS priority
        """
        with self.driver.session() as session:
            result = session.run(
                query,
                customer_id=customer_id,
                category=issue_category
            )
            record = result.single()
            return dict(record) if record else {}

    def handle_ticket(self, customer_id: str, issue_text: str) -> str:
        """チケットを受け取り、KG情報を参照してAgentが応答を生成"""
        # KGからコンテキスト取得（Read）
        # まずLLMでカテゴリを判定
        category = self.llm.invoke(
            f"次のサポートチケットのカテゴリを1単語で答えてください: {issue_text}"
        ).strip()

        routing_info = self.get_routing_info(customer_id, category)

        # KGの情報をコンテキストに含めて回答生成
        prompt = f"""あなたはカスタマーサポートエージェントです。
以下のコンテキストを参照して回答してください:
- 担当チーム: {routing_info.get('team_name', '未定')}
- SLA: {routing_info.get('sla_hours', 'N/A')}時間以内
- 優先度: {routing_info.get('priority', '通常')}

ユーザーの問い合わせ: {issue_text}
"""
        return self.llm.invoke(prompt)

    def close(self):
        self.driver.close()


# クラウドLLMを使う場合（オプション）
# from langchain_anthropic import ChatAnthropic
# self.llm = ChatAnthropic(model="claude-sonnet-4-6")


if __name__ == "__main__":
    agent = SupportAgentWithKG(
        neo4j_uri=NEO4J_URI,
        neo4j_auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    try:
        # サンプルチケットで動作確認
        customer_id = "cust-001"
        issue_text = "APIの認証エラーが頻発しています。本番環境で影響が出ています。"

        print(f"顧客ID: {customer_id}")
        print(f"問い合わせ: {issue_text}")
        print("-" * 50)

        response = agent.handle_ticket(customer_id, issue_text)
        print(f"エージェント応答:\n{response}")
    finally:
        agent.close()
