"""共通: Neo4j / Qdrant / SQLite / Ollama 接続と CLI 出力ヘルパー."""

from __future__ import annotations

import atexit
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

try:
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover
    ChatOllama = None  # type: ignore[misc, assignment]

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_LLM_MODEL = "gemma2:2b"

# 通し題材の障害チケット ID（seed・全レイヤーで共有）
ISSUE_ID = "INC-001"

for env_name in (".env", "env.sample"):
    env_path = ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break


def confirm_block(title: str, lines: list[str]) -> None:
    print(f"\n=== 確認 — {title} ===")
    for line in lines:
        print(line)
    print()


_DRIVER = None


def neo4j_driver():
    """プロセス内で1つの Driver を使い回す（接続プールの都度生成を避ける）."""
    global _DRIVER
    if _DRIVER is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        _DRIVER = GraphDatabase.driver(uri, auth=(user, password))
        atexit.register(_DRIVER.close)
    return _DRIVER


@contextmanager
def neo4j_session():
    """使い回しの Driver から session を1つ開く。クエリ関数はこれを使う."""
    with neo4j_driver().session() as session:
        yield session


def run_cypher_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    # コメントは行単位で除去してから文単位に分割する。
    # （文頭にコメント行が付くと DETACH DELETE 等が丸ごと捨てられるため）
    no_comments = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("//")
    )
    statements = [s.strip() for s in no_comments.split(";") if s.strip()]
    with neo4j_session() as session:
        for stmt in statements:
            session.run(stmt)


def audit_db_path() -> Path:
    raw = os.getenv("AUDIT_DB_PATH", "audit.db")
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


def init_audit_db() -> None:
    db = audit_db_path()
    if db.exists():
        db.unlink()
    conn = sqlite3.connect(db)
    try:
        sql = (DATA_DIR / "audit_seed.sql").read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ollama_available() -> bool:
    import urllib.error
    import urllib.request

    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    try:
        urllib.request.urlopen(f"{base}/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def get_llm():
    if ChatOllama is None:
        raise RuntimeError("langchain-ollama がインストールされていません")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_LLM_MODEL", DEFAULT_LLM_MODEL)
    return ChatOllama(model=model, base_url=base_url, temperature=0)
