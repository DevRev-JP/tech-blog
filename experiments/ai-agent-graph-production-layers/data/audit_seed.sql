CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action_type TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  issue_id TEXT,
  product_name TEXT,
  severity TEXT,
  created_at TEXT NOT NULL
);

INSERT INTO audit_log (action_type, actor_id, issue_id, product_name, severity, created_at) VALUES
  ('escalated', 'agent_incident_bot', 'INC-001', 'Acme Search', 'P0', datetime('now', '-2 days')),
  ('escalated', 'agent_incident_bot', 'INC-00042', 'Acme Search', 'P1', datetime('now', '-10 days')),
  ('escalated', 'oncall_alice', 'INC-00017', 'Acme Search', 'P0', datetime('now', '-25 days')),
  ('escalated', 'oncall_bob', 'INC-00005', 'Platform Logging', 'P0', datetime('now', '-28 days')),
  ('updated', 'agent_incident_bot', 'INC-001', 'Acme Search', 'P0', datetime('now', '-1 days'));
