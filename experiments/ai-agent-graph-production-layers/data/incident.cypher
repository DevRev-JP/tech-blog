// 障害対応 PoC seed — 第1部5種 + 第2部6特殊化（Edge 型で論理分離）
MATCH (n) DETACH DELETE n;

CREATE (cust:Customer {id: 'globex', name: 'Globex Corp'})
CREATE (prod:Product {id: 'acme-search', name: 'Acme Search'})
CREATE (issue:Issue {id: 'INC-001', title: 'Search latency spike', severity: 'P0'})
CREATE (issue)-[:AFFECTS]->(prod)
CREATE (prod)-[:OWNED_BY]->(cust);

MATCH (prod:Product {id: 'acme-search'})
CREATE (logging:Service {id: 'logging-pipeline', name: 'Platform Logging'})
CREATE (search:Service {id: 'search-api', name: 'Search API'})
CREATE (logging)-[:BLOCKS]->(search)
CREATE (prod)-[:DEPENDS_ON]->(search);

MATCH (issue:Issue {id: 'INC-001'}), (prod:Product {id: 'acme-search'})
CREATE (agent:Agent {id: 'agent_incident_bot', name: 'Incident Bot'})
CREATE (guest:Agent {id: 'agent_guest', name: 'Guest Agent'})
CREATE (agent)-[:CAN_READ]->(issue)
CREATE (guest)-[:CAN_READ]->(prod);

MATCH (cust:Customer {id: 'globex'})
CREATE (slack:ChannelAccount {id: 'slack-globex-support', channel: 'globex-support'})
CREATE (email:ChannelAccount {id: 'email-globex-ops', address: 'ops@globex.example'})
CREATE (slack)-[:SAME_AS]->(cust)
CREATE (email)-[:SAME_AS]->(cust);

CREATE (t1:IncidentTask {id: 'task-triage', name: 'Triage ticket'})
CREATE (t2:IncidentTask {id: 'task-logging', name: 'Restore logging pipeline'})
CREATE (t3:IncidentTask {id: 'task-root-cause', name: 'Identify root cause'})
CREATE (t1)-[:TASK_PREREQUISITE]->(t2)
CREATE (t2)-[:TASK_PREREQUISITE]->(t3);

CREATE (ws1:WfStep {id: 'wf-investigating', name: 'Investigating'})
CREATE (ws2:WfStep {id: 'wf-review', name: 'Human review'})
CREATE (ws3:WfStep {id: 'wf-done', name: 'Done'})
CREATE (ws1)-[:WF_TRANSITION {action: 'submit'}]->(ws2)
CREATE (ws2)-[:WF_TRANSITION {action: 'approve'}]->(ws3)
CREATE (ws2)-[:WF_TRANSITION {action: 'reject'}]->(ws1);

MATCH (issue:Issue {id: 'INC-001'})
CREATE (e1:Event {id: 'evt-release', name: 'Release v2.3.1 deployed', at: '2026-07-10T14:00:00Z'})
CREATE (e2:Event {id: 'evt-latency', name: 'Latency spike detected', at: '2026-07-10T14:25:00Z'})
CREATE (e3:Event {id: 'evt-escalate', name: 'Escalated to P0', at: '2026-07-10T14:30:00Z'})
CREATE (e1)-[:BEFORE]->(e2)
CREATE (e2)-[:BEFORE]->(e3)
CREATE (e2)-[:CAUSED_BY]->(e1)
CREATE (issue)-[:ESCALATED_AT]->(e3)
SET issue.escalated_at = '2026-07-10T14:30:00Z';

MATCH (issue:Issue {id: 'INC-001'})
CREATE (alice:Actor {id: 'oncall_alice', name: 'Alice'})
CREATE (act:AuditAction {id: 'act-update-inc001', name: 'update_ticket', tool: 'update_ticket'})
CREATE (alice)-[:PERFORMED {at: '2026-07-10T15:00:00Z'}]->(act)
CREATE (act)-[:ON_ISSUE]->(issue);

MATCH (issue:Issue {id: 'INC-001'}), (prod:Product {id: 'acme-search'}), (cust:Customer {id: 'globex'})
CREATE (scope:ContextScope {id: 'scope-engineer', max_hops: 2})
CREATE (scope)-[:SCOPE_INCLUDES]->(issue)
CREATE (scope)-[:SCOPE_INCLUDES]->(prod)
CREATE (scope)-[:SCOPE_INCLUDES]->(cust);
