"""
KG（意味レイヤ）の最小構成例: クエリの実行

記事「LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド」の
ハンズオンセクション「Neo4j + Cypher の最小例」に対応する例です。

実行方法:
    python query.py
"""

from neo4j import GraphDatabase

# Neo4j 接続情報
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def run_query():
    """記事で説明されているクエリ例を実行"""
    with driver.session() as session:
        # 記事の例: 顧客のSLA優先度を取得
        result = session.run("""
            MATCH (c:Customer {id: "CUST-123"})-[:HAS_CONTRACT]->(:Contract)-[:ON_PLAN]->(:Plan)-[:HAS_SLA]->(s:SLA)
            RETURN s.priority;
        """)
        
        print("クエリ結果:")
        for record in result:
            print(f"  SLA Priority: {record['s.priority']}")

if __name__ == "__main__":
    try:
        run_query()
    finally:
        driver.close()

