"""
アンチパターン: LLM に直接 SQL を書かせてしまう危険な実装

この実装は、LLM が生成した SQL 文字列をそのまま実行してしまいます。
SQL インジェクションや意図しないデータ操作のリスクがあります。
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI(title="Unsafe SQL Layer (Anti-pattern)", version="1.0.0")

DB_PATH = "/tmp/unsafe_billing.db"


class SQLRequest(BaseModel):
    sql: str  # LLM が生成した SQL 文字列（危険！）


def init_db():
    """危険な例のためのデータベース初期化"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL
        )
    """)
    cursor.execute("DELETE FROM billing")
    cursor.executemany(
        "INSERT INTO billing (customer_id, amount, status) VALUES (?, ?, ?)",
        [
            ("CUST-123", 1000, "open"),
            ("CUST-123", 2000, "closed"),
            ("CUST-456", 1500, "open"),
        ]
    )
    conn.commit()
    conn.close()


init_db()


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "unsafe-sql-layer", "warning": "This is an anti-pattern example!"}


@app.post("/execute")
async def execute_sql(request: SQLRequest):
    """
    危険な実装: LLM が生成した SQL をそのまま実行
    
    問題点:
    - SQL インジェクションのリスク
    - 意図しないデータ操作（DELETE, DROP など）
    - 型安全性の欠如
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # ⚠️ 危険: LLM が生成した SQL をそのまま実行
        cursor.execute(request.sql)
        
        if request.sql.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()
            return {
                "sql": request.sql,
                "results": [dict(zip(columns, row)) for row in results],
                "warning": "This is unsafe! Use parameterized queries instead."
            }
        else:
            conn.commit()
            conn.close()
            return {
                "sql": request.sql,
                "message": "Query executed",
                "warning": "This is unsafe! Use parameterized queries instead."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

