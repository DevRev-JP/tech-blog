from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
import json, time, os

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j","password"))
time.sleep(3)
with driver.session() as s, open("seed.cypher") as f:
    cypher_content = f.read()
    statements = [stmt.strip() for stmt in cypher_content.split(";") if stmt.strip()]
    for stmt in statements:
        s.run(stmt)

client = QdrantClient(host="qdrant", port=6333)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
docs_file = os.getenv("DOCS_FILE", "docs.jsonl")
texts = [json.loads(l) for l in open(docs_file)]
vecs = model.encode([t["text"] for t in texts])

if "docs" not in [c.name for c in client.get_collections().collections]:
    client.recreate_collection(
        collection_name="docs",
        vectors_config=VectorParams(size=len(vecs[0]), distance=Distance.COSINE)
    )

points = [PointStruct(id=i+1, vector=vecs[i], payload=texts[i]) for i in range(len(texts))]
client.upsert(collection_name="docs", points=points)
print("Seed done")