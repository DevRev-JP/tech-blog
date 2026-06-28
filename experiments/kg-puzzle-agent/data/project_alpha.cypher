MATCH (n) DETACH DELETE n;

CREATE (p:Project {name: 'Alpha', deadline: '2024Q4', visibility: 'internal'})
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

CREATE (u_tanaka:User {id: 'user_tanaka', name: 'tanaka'})
CREATE (u_guest:User {id: 'user_guest', name: 'guest'})
CREATE (u_tanaka)-[:MEMBER_OF]->(t)
CREATE (t)-[:HAS_ACCESS_TO]->(p);
