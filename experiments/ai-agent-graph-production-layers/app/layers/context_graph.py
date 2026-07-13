"""[2部] Q8 コンテキストグラフ（部分サブグラフ）."""

from __future__ import annotations

from app.shared import neo4j_session

DEFAULT_SCOPE = "scope-engineer"


def q8_context_nodes(scope_id: str = DEFAULT_SCOPE) -> list[dict]:
    cypher = """
    MATCH (s:ContextScope {id: $scope_id})-[:SCOPE_INCLUDES]->(n)
    WHERE n.id IS NOT NULL
    RETURN DISTINCT labels(n)[0] AS label,
           coalesce(n.id, n.name, n.title) AS node_id,
           coalesce(n.name, n.title, n.id) AS name
    ORDER BY label, node_id
    """
    with neo4j_session() as session:
        rows = session.run(cypher, scope_id=scope_id)
        return [dict(r) for r in rows]
