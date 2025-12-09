import express, { Request, Response } from "express";
import cors from "cors";
import Database from "better-sqlite3";
import * as path from "path";
import * as fs from "fs";

const app = express();
app.use(cors());
app.use(express.json());

const DB_PATH = process.env.DB_PATH || "/data/billing.db";

// Initialize database
function initDatabase() {
  const dbDir = path.dirname(DB_PATH);
  if (!fs.existsSync(dbDir)) {
    fs.mkdirSync(dbDir, { recursive: true });
  }

  const db = new Database(DB_PATH);
  
  // Read and execute schema
  // Try multiple possible paths (for both dev and production)
  const possiblePaths = [
    path.join(__dirname, "../schema.sql"),
    path.join(process.cwd(), "schema.sql"),
    "/app/schema.sql"
  ];
  
  let schemaLoaded = false;
  for (const schemaPath of possiblePaths) {
    if (fs.existsSync(schemaPath)) {
      const schema = fs.readFileSync(schemaPath, "utf-8");
      db.exec(schema);
      schemaLoaded = true;
      break;
    }
  }
  
  if (!schemaLoaded) {
    // Fallback: create table directly
    db.exec(`
      CREATE TABLE IF NOT EXISTS billing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('open', 'closed'))
      );
      INSERT OR IGNORE INTO billing (customer_id, amount, status) VALUES
        ('CUST-123', 1000, 'open'),
        ('CUST-123', 2000, 'closed'),
        ('CUST-456', 1500, 'open'),
        ('CUST-789', 3000, 'open');
    `);
  }
  
  return db;
}

const db = initDatabase();

// Types
type BillingQuery = {
  customerId: string;
  mode: "open" | "all";
};

// Health check
app.get("/healthz", (req: Request, res: Response) => {
  try {
    db.prepare("SELECT 1").get();
    res.json({ status: "ok", service: "sql-layer" });
  } catch (error) {
    res.status(500).json({ status: "error", error: String(error) });
  }
});

// Query endpoint
app.post("/query", (req: Request, res: Response) => {
  try {
    const query: BillingQuery = req.body;
    
    if (!query.customerId || !query.mode) {
      return res.status(400).json({ 
        error: "Invalid request. Required: customerId, mode ('open' | 'all')" 
      });
    }

    let result;
    if (query.mode === "open") {
      result = db
        .prepare(
          "SELECT id, customer_id, amount, status FROM billing WHERE customer_id = ? AND status='open'"
        )
        .all(query.customerId);
    } else {
      result = db
        .prepare("SELECT id, customer_id, amount, status FROM billing WHERE customer_id = ?")
        .all(query.customerId);
    }

    res.json({
      query,
      results: result,
      count: result.length
    });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

// Get all billing records (for testing)
app.get("/billing", (req: Request, res: Response) => {
  try {
    const result = db.prepare("SELECT * FROM billing").all();
    res.json({ results: result });
  } catch (error) {
    res.status(500).json({ error: String(error) });
  }
});

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {
  console.log(`SQL Layer API running on port ${PORT}`);
  console.log(`Database: ${DB_PATH}`);
});

