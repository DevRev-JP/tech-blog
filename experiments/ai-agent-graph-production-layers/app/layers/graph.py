"""[1部] ナレッジグラフ + [2部] Q3 依存 / Q4 権限."""

from __future__ import annotations

from app.shared import ISSUE_ID, neo4j_session


def q1_customer(issue_id: str = ISSUE_ID) -> dict:
    cypher = """
    MATCH (i:Issue {id: $issue_id})-[:AFFECTS]->(p:Product)-[:OWNED_BY]->(c:Customer)
    RETURN i.id AS issue, p.name AS product, c.name AS customer
    """
    with neo4j_session() as session:
        rec = session.run(cypher, issue_id=issue_id).single()
    return dict(rec) if rec else {}


def q3_blocked_services(service_id: str = "logging-pipeline") -> list[str]:
    cypher = """
    MATCH (s:Service {id: $sid})-[:BLOCKS]->(blocked:Service)
    RETURN DISTINCT blocked.name AS name
    ORDER BY name
    """
    with neo4j_session() as session:
        rows = session.run(cypher, sid=service_id)
        return [r["name"] for r in rows]


def q4_can_read(agent_id: str, issue_id: str = ISSUE_ID) -> bool:
    cypher = """
    MATCH (a:Agent {id: $agent_id})-[:CAN_READ]->(i:Issue {id: $issue_id})
    RETURN count(i) > 0 AS allowed
    """
    with neo4j_session() as session:
        rec = session.run(cypher, agent_id=agent_id, issue_id=issue_id).single()
    return bool(rec["allowed"]) if rec else False
