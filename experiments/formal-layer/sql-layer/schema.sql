CREATE TABLE IF NOT EXISTS billing (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('open', 'closed'))
);

-- Insert sample data
INSERT INTO billing (customer_id, amount, status) VALUES
  ('CUST-123', 1000, 'open'),
  ('CUST-123', 2000, 'closed'),
  ('CUST-456', 1500, 'open'),
  ('CUST-789', 3000, 'open');

