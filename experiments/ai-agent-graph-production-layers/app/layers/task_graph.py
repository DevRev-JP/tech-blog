"""[1部] タスクグラフ."""

from __future__ import annotations

from app.shared import neo4j_session


def task_prerequisites() -> list[tuple[str, str]]:
    cypher = """
    MATCH (a:IncidentTask)-[:TASK_PREREQUISITE]->(b:IncidentTask)
    RETURN a.name AS from_task, b.name AS to_task
    ORDER BY from_task
    """
    with neo4j_session() as session:
        rows = session.run(cypher)
        return [(r["from_task"], r["to_task"]) for r in rows]
