"""Q2 類似障害 — Qdrant.

埋め込みは Ollama の埋め込みモデル（既定 nomic-embed-text）を使う。
Ollama が使えない場合のみ、決定的な疑似ベクトルにフォールバックする
（この場合は「意味的類似」にならず、Q2 の体験が成立しない点に注意）。
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.shared import DATA_DIR

COLLECTION = os.getenv("QDRANT_COLLECTION", "incident_docs")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
EMBED_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
FALLBACK_DIM = 768  # nomic-embed-text と同次元（フォールバック時も collection を揃える）


def _client() -> QdrantClient:
    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        check_compatibility=False,
    )


def _hash_embed(text: str) -> list[float]:
    """フォールバック: 決定的な疑似ベクトル（意味は反映しない）."""
    h = hashlib.sha256(text.encode()).digest()
    return [(h[i % len(h)] / 255.0) * 2 - 1 for i in range(FALLBACK_DIM)]


def _ollama_embed(text: str) -> list[float] | None:
    """Ollama で埋め込みを取得。失敗時は None."""
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        data=json.dumps({"model": EMBED_MODEL, "prompt": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["embedding"]
    except (urllib.error.URLError, TimeoutError, OSError, KeyError):
        return None


def embed(text: str) -> list[float]:
    vec = _ollama_embed(text)
    return vec if vec is not None else _hash_embed(text)


def _embedding_dim() -> int:
    probe = _ollama_embed("dimension probe")
    return len(probe) if probe is not None else FALLBACK_DIM


def using_semantic_embedding() -> bool:
    """意味的埋め込み（Ollama）が使えるかどうか."""
    return _ollama_embed("probe") is not None


def seed_collection() -> int:
    client = _client()
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=_embedding_dim(), distance=Distance.COSINE),
    )
    points: list[PointStruct] = []
    path = DATA_DIR / "incident_docs.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        doc = json.loads(line)
        text = f"{doc['title']} {doc['summary']} {doc['product']}"
        points.append(
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, doc["id"])),
                vector=embed(text),
                payload=doc,
            )
        )
    client.upsert(collection_name=COLLECTION, points=points)
    return len(points)


def q2_similar(query: str, limit: int = 2) -> list[dict]:
    client = _client()
    result = client.query_points(
        collection_name=COLLECTION,
        query=embed(query),
        limit=limit,
    )
    return [p.payload for p in result.points if p.payload]
