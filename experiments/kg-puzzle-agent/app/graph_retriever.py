"""権限付きグラフコンテキスト取得.

本番では質問からエンティティ解決・GraphRAG 等が要る。本 experiment では Project Alpha 固定の
簡略 Cypher のみ（README #demo-vs-production）。権限付きパストラバーサルの形は本物。
"""

from __future__ import annotations

import re


class GraphRetriever:
    def __init__(self, driver):
        self.driver = driver

    def _extract_key_entities(self, query: str) -> list[str]:
        # デモ簡略: 質問内容に関わらず Alpha のみ（本番はエンティティリンク等）
        if re.search(r"Alpha|アルファ|alpha", query, re.I):
            return ["Alpha"]
        return ["Alpha"]

    def get_context_with_permissions(self, query: str, user_id: str, depth: int = 2) -> str:
        _ = depth
        entities = self._extract_key_entities(query)
        lines: list[str] = []

        with self.driver.session() as session:
            for entity_name in entities:
                result = session.run(
                    """
                    MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(:Team)-[:HAS_ACCESS_TO]->(p:Project {name: $name})
                    OPTIONAL MATCH (p)-[r]-(n)
                    WHERE n:Team OR n:Person OR n:TechStack
                    OPTIONAL MATCH (p)-[:HAS_DEAL]->(deal:Deal)
                    RETURN p.name AS project,
                           p.deadline AS deadline,
                           collect(DISTINCT
                             CASE labels(n)[0]
                               WHEN 'Team' THEN 'Team:' + n.name
                               WHEN 'Person' THEN 'Person:' + n.name
                               WHEN 'TechStack' THEN 'TechStack:' + n.name
                               ELSE labels(n)[0]
                             END) AS nodes,
                           collect(DISTINCT
                             startNode(r).name + ' --[' + type(r) + ']--> ' + endNode(r).name
                           ) AS edges,
                           deal.customer AS deal_customer,
                           deal.budget_confidential AS deal_budget
                    """,
                    user_id=user_id,
                    name=entity_name,
                ).single()

                if not result or not result.get("project"):
                    lines.append(f"[Project:{entity_name}] — アクセス権限がありません")
                    continue

                lines.append(f"[Project:{result['project']}] deadline={result['deadline']}")
                for node in result.get("nodes") or []:
                    if node:
                        lines.append(f"  ({node})")
                for edge in result.get("edges") or []:
                    if edge and "--" in edge:
                        lines.append(f"  {edge}")
                if result.get("deal_customer"):
                    lines.append(
                        f"  (Deal:{result['deal_customer']} budget={result.get('deal_budget') or '—'})"
                    )

        return "\n".join(lines) if lines else "（このユーザーがアクセス可能なプロジェクトはありません）"
