"""
agent_langchain.py
LangChain Tool + AgentExecutor によるKGクエリのツール化。

ch8「AI AgentとKG」のLangChainツール定義実装例。
KGへのクエリをAgentが呼び出せるツールとして定義し、
AgentExecutorで質問に応じて自律的にツールを使い回答を生成する。

参照: books/knowledge-graph-llm-guide/kg-and-ai-agents.md
"""

import os

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM
from neo4j import GraphDatabase

# .envを読み込む
load_dotenv()

# グローバルなドライバー（実際は依存性注入を使う）
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

assert NEO4J_PASSWORD, "NEO4J_PASSWORD環境変数を設定してください（.envファイル推奨）"

_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@tool
def search_customer_info(customer_name: str) -> str:
    """
    顧客名でKGを検索し、顧客情報・担当チーム・プランを返す。
    顧客に関する質問があればこのツールを使う。
    """
    query = """
    MATCH (c:Customer)
    WHERE c.name CONTAINS $name
    OPTIONAL MATCH (c)-[:HAS_PLAN]->(plan:Plan)
    OPTIONAL MATCH (plan)-[:SUPPORTED_BY]->(team:SupportTeam)
    RETURN
        c.name AS customer_name,
        plan.name AS plan,
        plan.tier AS tier,
        team.name AS support_team,
        team.sla_hours AS sla_hours
    LIMIT 5
    """
    with _driver.session() as session:
        result = session.run(query, name=customer_name)
        records = [dict(r) for r in result]
        if not records:
            return f"顧客 '{customer_name}' は見つかりませんでした"
        return str(records)


@tool
def get_related_incidents(service_name: str) -> str:
    """
    サービス名でKGを検索し、関連インシデントの履歴を返す。
    障害やインシデントに関する質問があればこのツールを使う。
    """
    query = """
    MATCH (s:Service {name: $service_name})<-[:AFFECTS]-(i:Incident)
    RETURN
        i.title AS title,
        i.severity AS severity,
        i.resolved_at AS resolved_at,
        i.mttr_minutes AS mttr
    ORDER BY i.resolved_at DESC
    LIMIT 5
    """
    with _driver.session() as session:
        result = session.run(query, service_name=service_name)
        records = [dict(r) for r in result]
        return str(records) if records else f"'{service_name}'の過去インシデントはありません"


# AgentにツールをバインドしてAgentExecutorを構成
llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)
tools = [search_customer_info, get_related_incidents]

# クラウドLLMを使う場合（オプション）
# from langchain_anthropic import ChatAnthropic
# llm = ChatAnthropic(model="claude-sonnet-4-6")

prompt = ChatPromptTemplate.from_messages([
    ("system", "あなたは社内情報に詳しいAIアシスタントです。必要に応じてツールを使って正確な情報を提供してください。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


if __name__ == "__main__":
    # 実行例：顧客情報の検索
    response = executor.invoke({
        "input": "サンライズテックのサポートプランと担当チームを教えてください"
    })
    print(response["output"])
