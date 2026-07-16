"""[2部] 監査グラフ（Q6）— SQLite 集計 + Neo4j PERFORMED."""

from __future__ import annotations

import sqlite3

from app.shared import ISSUE_ID, audit_db_path, neo4j_session


def q5_p0_top_products(days: int = 30, limit: int = 5) -> list[dict]:
    conn = sqlite3.connect(audit_db_path())
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT product_name, COUNT(*) AS cnt
            FROM audit_log
            WHERE severity = 'P0'
              AND action_type = 'escalated'
              AND created_at >= datetime('now', ?)
            GROUP BY product_name
            ORDER BY cnt DESC
            LIMIT ?
            """,
            (f"-{days} days", limit),
        ).fetchall()
        return [{"product": r["product_name"], "p0_count": r["cnt"]} for r in rows]
    finally:
        conn.close()


def performed_actions(issue_id: str = ISSUE_ID) -> list[dict]:
    cypher = """
    MATCH (a:Actor)-[p:PERFORMED]->(act:AuditAction)-[:ON_ISSUE]->(i:Issue {id: $issue_id})
    RETURN a.id AS actor, act.tool AS tool, p.at AS at
    ORDER BY at
    """
    with neo4j_session() as session:
        rows = session.run(cypher, issue_id=issue_id)
        return [dict(r) for r in rows]
