import os
# pip install langchain-neo4j langchain-ollama
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_ollama import OllamaLLM

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
assert NEO4J_PASSWORD, "NEO4J_PASSWORD環境変数を設定してください（.envファイル推奨）"

# Neo4jGraphはスキーマを自動取得してLLMのプロンプトに含める
graph = Neo4jGraph(
    url=NEO4J_URI,
    username=NEO4J_USER,
    password=NEO4J_PASSWORD
)

# スキーマを確認（LLMへのコンテキストとして使われる）
print(graph.schema)
# 出力例:
# Node properties are the following:
# Engineer {id: STRING, name: STRING, team: STRING}
# Bug {id: STRING, title: STRING, severity: STRING, status: STRING}
# Relationship properties are the following:
# ASSIGNED_TO {}
# The relationships are the following:
# (:Bug)-[:ASSIGNED_TO]->(:Engineer)

# ローカルLLM（Ollama）でチェーンを設定
llm = OllamaLLM(model="llama3.2", base_url="http://localhost:11434")

chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True,       # 生成されたCypherクエリを出力
    return_intermediate_steps=True,  # デバッグ用
    # セキュリティ注意：LLMが生成したCypherを無検証で実行します。
    # 本番環境では読み取り専用ユーザーで実行するか、生成クエリを事前検証してください。
    allow_dangerous_requests=True,   # LangChain v0.2以降は必要
)

# 自然言語で質問
questions = [
    "criticalなオープンバグは何件ありますか？",
    "山田太郎が担当しているバグのタイトルを教えてください",
    "Backendチームのエンジニアが担当しているバグ一覧を教えてください",
]

for q in questions:
    print(f"\n質問: {q}")
    result = chain.invoke({"query": q})
    print(f"回答: {result['result']}")
    # intermediate_stepsでLLMが生成したCypherクエリも確認できる
    cypher = result["intermediate_steps"][0]["query"]
    print(f"生成されたCypher: {cypher}")

# クラウドLLMを使う場合（オプション）
# from langchain_anthropic import ChatAnthropic
# llm = ChatAnthropic(model="claude-sonnet-4-6")
