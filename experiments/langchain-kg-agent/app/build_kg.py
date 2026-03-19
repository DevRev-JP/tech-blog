"""
build_kg.py
サンプルデータ（customers.csv / tickets.csv）をNeo4jに投入するスクリプト。

使い方:
    cp .env.example .env  # .envを作成して各値を設定
    python app/build_kg.py
"""

import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

# .envを読み込む
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

assert NEO4J_PASSWORD, "NEO4J_PASSWORD環境変数を設定してください（.envファイル推奨）"

DATA_DIR = Path(__file__).parent.parent / "data"


def load_customers(driver):
    """customers.csvを読み込み、Customer・Plan・SupportTeamノードとリレーションを作成する"""
    with open(DATA_DIR / "customers.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with driver.session() as session:
        for row in rows:
            session.run(
                """
                MERGE (c:Customer {id: $customer_id})
                SET c.name = $customer_name

                MERGE (plan:Plan {name: $plan_name})
                SET plan.tier = $plan_tier

                MERGE (team:SupportTeam {name: $support_team})
                SET team.sla_hours = toInteger($sla_hours)

                MERGE (c)-[:HAS_PLAN]->(plan)
                MERGE (plan)-[:SUPPORTED_BY]->(team)
                """,
                customer_id=row["customer_id"],
                customer_name=row["customer_name"],
                plan_name=row["plan_name"],
                plan_tier=row["plan_tier"],
                support_team=row["support_team"],
                sla_hours=row["sla_hours"],
            )
    print(f"顧客データ {len(rows)} 件を投入しました")


def load_tickets(driver):
    """tickets.csvを読み込み、Ticketノードと(Customer)-[:SUBMITTED]->(Ticket)を作成する"""
    with open(DATA_DIR / "tickets.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with driver.session() as session:
        for row in rows:
            session.run(
                """
                MATCH (c:Customer {id: $customer_id})
                MERGE (t:Ticket {id: $ticket_id})
                SET t.message = $message,
                    t.category = $category,
                    t.created_at = datetime($created_at),
                    t.escalated = ($escalated = 'true')
                MERGE (c)-[:SUBMITTED]->(t)
                """,
                ticket_id=row["ticket_id"],
                customer_id=row["customer_id"],
                message=row["message"],
                category=row["category"],
                created_at=row["created_at"],
                escalated=row["escalated"],
            )
    print(f"チケットデータ {len(rows)} 件を投入しました")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        print("Neo4jへの接続を確認中...")
        driver.verify_connectivity()
        print("接続OK")

        print("顧客データを投入中...")
        load_customers(driver)

        print("チケットデータを投入中...")
        load_tickets(driver)

        print("データ投入完了。Neo4j Browser ( http://localhost:7474 ) で確認できます。")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
