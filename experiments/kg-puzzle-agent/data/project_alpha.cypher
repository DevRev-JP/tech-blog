MATCH (n) DETACH DELETE n;

CREATE (p:Project {name: 'Alpha', deadline: '2026Q3', visibility: 'internal'})
CREATE (t:Team {name: 'Team A'})
CREATE (p)-[:OWNED_BY]->(t)

CREATE (leader:Person {name: '田中'})
CREATE (m1:Person {name: '佐藤'})
CREATE (m2:Person {name: '鈴木'})
CREATE (t)-[:HAS_LEADER]->(leader)
CREATE (t)-[:HAS_MEMBER]->(m1)
CREATE (t)-[:HAS_MEMBER]->(m2)

CREATE (tech:TechStack {name: 'Python + Neo4j'})
CREATE (p)-[:USES]->(tech)

CREATE (deal:Deal {customer: '顧客X', note: 'Project Alpha 拡張案件', budget_confidential: '800万（社外秘）'})
CREATE (p)-[:HAS_DEAL]->(deal)

CREATE (u_tanaka:User {id: 'user_tanaka', name: 'tanaka'})
CREATE (u_guest:User {id: 'user_guest', name: 'guest'})
CREATE (u_tanaka)-[:MEMBER_OF]->(t)
CREATE (t)-[:HAS_ACCESS_TO]->(p);
