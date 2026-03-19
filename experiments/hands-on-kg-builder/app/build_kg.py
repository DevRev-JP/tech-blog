import csv
from neo4j import GraphDatabase
from typing import Optional

class KnowledgeGraphBuilder:
    def __init__(self, uri: str, auth: Optional[tuple] = None):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def load_engineers(self, csv_path: str):
        """エンジニアCSVをNeo4jに投入"""
        with open(csv_path, "r", encoding="utf-8") as f:
            engineers = list(csv.DictReader(f))

        with self.driver.session() as session:
            # バッチ処理でパフォーマンスを改善
            session.execute_write(self._batch_create_engineers, engineers)
        print(f"  {len(engineers)} 人のエンジニアを投入しました")

    @staticmethod
    def _batch_create_engineers(tx, engineers: list):
        """MERGEを使った冪等な一括投入"""
        query = """
        UNWIND $engineers AS eng
        MERGE (e:Engineer {id: eng.id})
        ON CREATE SET
            e.name = eng.name,
            e.team = eng.team,
            e.email = eng.email,
            e.createdAt = datetime()
        ON MATCH SET
            e.name = eng.name,
            e.team = eng.team,
            e.updatedAt = datetime()
        """
        tx.run(query, engineers=engineers)

    def load_bugs(self, csv_path: str):
        """バグCSVをNeo4jに投入し、担当者との関係も作成"""
        with open(csv_path, "r", encoding="utf-8") as f:
            bugs = list(csv.DictReader(f))

        with self.driver.session() as session:
            session.execute_write(self._batch_create_bugs, bugs)
        print(f"  {len(bugs)} 件のバグを投入しました")

    @staticmethod
    def _batch_create_bugs(tx, bugs: list):
        query = """
        UNWIND $bugs AS bug
        MERGE (b:Bug {id: bug.id})
        ON CREATE SET
            b.title     = bug.title,
            b.severity  = bug.severity,
            b.status    = bug.status,
            b.createdAt = datetime()
        ON MATCH SET
            b.status    = bug.status,
            b.updatedAt = datetime()
        WITH b, bug
        // 担当者エンジニアが存在する場合のみ関係を作成
        WHERE bug.assignee_id <> ""
        MATCH (e:Engineer {id: bug.assignee_id})
        MERGE (b)-[:ASSIGNED_TO]->(e)
        """
        tx.run(query, bugs=bugs)

    def create_indexes(self):
        """検索高速化のためのインデックス作成"""
        with self.driver.session() as session:
            indexes = [
                "CREATE INDEX engineer_id IF NOT EXISTS FOR (e:Engineer) ON (e.id)",
                "CREATE INDEX bug_id IF NOT EXISTS FOR (b:Bug) ON (b.id)",
                "CREATE INDEX bug_severity IF NOT EXISTS FOR (b:Bug) ON (b.severity)",
                "CREATE INDEX bug_status IF NOT EXISTS FOR (b:Bug) ON (b.status)",
            ]
            for index_query in indexes:
                session.run(index_query)
        print("  インデックスを作成しました")


def main():
    import os
    # ローカルDocker環境への接続（環境変数からパスワードを取得）
    builder = KnowledgeGraphBuilder(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD")  # .envで設定必須
        )
    )

    try:
        builder.create_indexes()
        builder.load_engineers("data/engineers.csv")
        builder.load_bugs("data/bugs.csv")
        print("KG構築完了")
    finally:
        builder.close()


if __name__ == "__main__":
    main()
