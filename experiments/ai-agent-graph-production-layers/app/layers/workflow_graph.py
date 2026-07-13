"""[1部] ワークフローグラフ."""

from __future__ import annotations

from app.shared import neo4j_session


def workflow_transitions() -> list[dict]:
    cypher = """
    MATCH (a:WfStep)-[t:WF_TRANSITION]->(b:WfStep)
    RETURN a.name AS from_step, t.action AS action, b.name AS to_step
    ORDER BY from_step, action
    """
    with neo4j_session() as session:
        rows = session.run(cypher)
        return [dict(r) for r in rows]
