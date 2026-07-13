"""[2部] Q6 同一性グラフ."""

from __future__ import annotations

from app.shared import neo4j_session


def q6_same_customer(channel_ids: list[str]) -> dict:
    cypher = """
    UNWIND $ids AS cid
    MATCH (ch:ChannelAccount {id: cid})-[:SAME_AS]->(c:Customer)
    RETURN cid, c.id AS customer_id, c.name AS customer_name
    """
    with neo4j_session() as session:
        rows = session.run(cypher, ids=channel_ids)
        mapping = {r["cid"]: r["customer_name"] for r in rows}
    names = set(mapping.values())
    return {
        "channels": mapping,
        "same_customer": len(names) == 1,
        "customer": next(iter(names), None),
    }
