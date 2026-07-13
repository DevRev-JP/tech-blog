"""[2部] Q7 時間軸グラフ."""

from __future__ import annotations

from app.shared import neo4j_driver

ISSUE_ID = "INC-001"


def q7_events_before_escalation(issue_id: str = ISSUE_ID, minutes: int = 30) -> list[dict]:
    cypher = """
    MATCH (i:Issue {id: $issue_id})-[:ESCALATED_AT]->(esc:Event)
    MATCH (e:Event)-[:BEFORE*]->(esc)
    WHERE e.at <= esc.at
    RETURN DISTINCT e.id AS id, e.name AS name, e.at AS at
    ORDER BY e.at
    """
    with neo4j_driver() as driver:
        rows = driver.session().run(cypher, issue_id=issue_id)
        return [dict(r) for r in rows]


def q7_escalated_at(issue_id: str = ISSUE_ID) -> str | None:
    cypher = """
    MATCH (i:Issue {id: $issue_id})
    RETURN i.escalated_at AS at
    """
    with neo4j_driver() as driver:
        rec = driver.session().run(cypher, issue_id=issue_id).single()
    return rec["at"] if rec else None
