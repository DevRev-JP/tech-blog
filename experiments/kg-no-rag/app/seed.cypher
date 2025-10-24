CREATE CONSTRAINT company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT product_name IF NOT EXISTS FOR (p:Product) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT feature_name IF NOT EXISTS FOR (f:Feature) REQUIRE f.name IS UNIQUE;
CREATE CONSTRAINT policy_id   IF NOT EXISTS FOR (r:Policy)  REQUIRE r.id   IS UNIQUE;

MERGE (ac:Company {name:"Acme"})     MERGE (gl:Company {name:"Globex"})
MERGE (pA:Product {name:"Acme Search"}) MERGE (pG:Product {name:"Globex Graph"})
MERGE (fSI:Feature {name:"Semantic Index"})
MERGE (fRT:Feature {name:"Realtime Query"})
MERGE (fPA:Feature {name:"Policy Audit"})

MERGE (pol1:Policy {id:"POL-001", title:"Personal Data Protection"})
MERGE (pol2:Policy {id:"POL-002", title:"AI Model Governance"})

MERGE (ac)-[:BUILDS]->(pA)
MERGE (gl)-[:BUILDS]->(pG)

MERGE (pA)-[:HAS_FEATURE]->(fSI)
MERGE (pA)-[:HAS_FEATURE]->(fRT)
MERGE (pG)-[:HAS_FEATURE]->(fSI)
MERGE (pG)-[:HAS_FEATURE]->(fPA)

MERGE (pol1)-[:REGULATES]->(pA)
MERGE (pol2)-[:REGULATES]->(pA)
MERGE (pol2)-[:REGULATES]->(pG)

MERGE (pG)-[:DEPENDS_ON]->(pA);