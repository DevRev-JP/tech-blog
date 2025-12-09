"""
KG（意味レイヤ）の最小構成例: データのシード

記事「LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド」の
ハンズオンセクション「Neo4j + Cypher の最小例」に対応する例です。

実行方法:
    python seed.py
"""

from neo4j import GraphDatabase

# Neo4j 接続情報
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def seed_data():
    """記事で説明されているモデル定義を実行"""
    with driver.session() as session:
        # 既存データをクリア
        session.run("MATCH (n) DETACH DELETE n")
        
        # 記事の例: Customer -> Contract -> Plan -> SLA
        session.run("""
            CREATE (:Customer {id:"CUST-123"})-[:HAS_CONTRACT]->
              (:Contract {id:"CON-1"})-[:ON_PLAN]->
              (:Plan {name:"Enterprise"})-[:HAS_SLA]->
              (:SLA {priority:"High"});
        """)
        print("✅ データのシードが完了しました")
        print("   Neo4j ブラウザで http://localhost:7474 を開いて確認できます")

if __name__ == "__main__":
    try:
        seed_data()
    finally:
        driver.close()

