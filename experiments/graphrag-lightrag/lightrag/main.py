import os
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

# Database clients (initialized on startup)
neo4j_driver = None
qdrant_client = None
embedding_model = None


class AskPayload(BaseModel):
    question: str
    top_k: int = Field(4, ge=1, le=20)
    depth: int = Field(2, ge=1, le=4)
    theta: float = Field(0.3, ge=0.0, le=1.0)


class AskResponse(BaseModel):
    answer: str
    vector_nodes: List[str]
    graph_nodes: List[str]
    subgraph: Optional[dict] = None
    metadata: dict


class FeedbackPayload(BaseModel):
    node_id: str
    weight: float = Field(..., ge=0.0, le=2.0)


app = FastAPI(title="LightRAG API", version="0.1.0")
feedback_log: List[FeedbackPayload] = []


class CompareResponse(BaseModel):
    question: str
    graphrag: dict
    lightrag: dict
    differences: dict


def _calc_differences(gr: dict, lr: dict) -> dict:
    diffs = {}
    # node counts (best-effort)
    gr_nodes = gr.get("graph_nodes") or gr.get("metadata", {}).get("graph_nodes") or []
    lr_nodes = lr.get("graph_nodes") or []
    diffs["node_count"] = {"graphrag": len(gr_nodes), "lightrag": len(lr_nodes)}
    return diffs


@app.on_event("startup")
async def startup_event():
    """Initialize database connections and embedding model on startup."""
    global neo4j_driver, qdrant_client, embedding_model
    
    # Initialize Neo4j driver
    try:
        from neo4j import GraphDatabase
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        # Test connection
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        print(f"✓ Neo4j connection established: {neo4j_uri}")
    except Exception as e:
        print(f"⚠ Neo4j connection failed (will retry): {e}")
        neo4j_driver = None
    
    # Initialize Qdrant client
    try:
        from qdrant_client import QdrantClient
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        # Test connection
        qdrant_client.get_collections()
        print(f"✓ Qdrant connection established: {qdrant_host}:{qdrant_port}")
    except Exception as e:
        print(f"⚠ Qdrant connection failed (will retry): {e}")
        qdrant_client = None
    
    # Initialize embedding model (for LightRAG vector retrieval)
    try:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        embedding_model = SentenceTransformer(model_name)
        print(f"✓ Embedding model loaded: {model_name}")
    except Exception as e:
        print(f"⚠ Embedding model loading failed: {e}")
        embedding_model = None
    
    # Initialize pipeline and seed data if clients are ready
    if neo4j_driver and qdrant_client:
        try:
            from pipeline import initialize_clients, seed_data
            initialize_clients(neo4j_driver, qdrant_client, embedding_model)
            data_file = os.getenv("DATA_FILE", "data/docs-light.jsonl")
            result = seed_data(data_file)
            print(f"✓ Data seeding: {result.get('status')}")
        except Exception as e:
            print(f"⚠ Data seeding failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown."""
    global neo4j_driver
    if neo4j_driver:
        neo4j_driver.close()
        print("✓ Neo4j connection closed")


@app.get("/healthz")
def healthcheck() -> dict:
    """Health check with DB connection status."""
    return {
        "status": "ok",
        "service": "lightrag-api",
        "version": app.version,
        "connections": {
            "neo4j": neo4j_driver is not None,
            "qdrant": qdrant_client is not None,
            "embedding_model": embedding_model is not None,
        },
    }


@app.get("/connections")
def check_connections() -> dict:
    """Check database connections and return detailed status."""
    result = {
        "neo4j": {"connected": False, "error": None},
        "qdrant": {"connected": False, "error": None},
        "embedding_model": {"loaded": embedding_model is not None},
    }
    
    # Test Neo4j
    if neo4j_driver:
        try:
            with neo4j_driver.session() as session:
                result_n = session.run("RETURN 1 AS test").single()
                result["neo4j"]["connected"] = True
                result["neo4j"]["test"] = result_n["test"] if result_n else None
        except Exception as e:
            result["neo4j"]["error"] = str(e)
    else:
        result["neo4j"]["error"] = "Driver not initialized"
    
    # Test Qdrant
    if qdrant_client:
        try:
            collections = qdrant_client.get_collections()
            result["qdrant"]["connected"] = True
            result["qdrant"]["collections"] = [c.name for c in collections.collections]
        except Exception as e:
            result["qdrant"]["error"] = str(e)
    else:
        result["qdrant"]["error"] = "Client not initialized"
    
    return result


@app.post("/ask", response_model=AskResponse)
def ask_question(payload: AskPayload) -> AskResponse:
    """Query LightRAG pipeline."""
    if not neo4j_driver or not qdrant_client:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Database connections not ready"
        )
    
    try:
        from pipeline import query_lightrag
        result = query_lightrag(
            question=payload.question,
            top_k=payload.top_k,
            depth=payload.depth,
            theta=payload.theta
        )
        
        metadata = {
            "question": payload.question,
            "params": payload.model_dump(exclude={"question"}),
            **result.get("metadata", {})
        }
        
        return AskResponse(
            answer=result.get("answer", "No answer generated"),
            vector_nodes=result.get("vector_nodes", []),
            graph_nodes=[n["name"] for n in result.get("graph_nodes", [])],
            subgraph=result.get("subgraph"),
            metadata=metadata
        )
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@app.post("/feedback")
def submit_feedback(payload: FeedbackPayload) -> dict:
    """Update edge weights (w_attn) in Neo4j based on feedback."""
    feedback_log.append(payload)
    
    # Update Neo4j edge weights
    if neo4j_driver:
        try:
            with neo4j_driver.session() as session:
                # Update w_attn for all edges connected to the specified node
                # Formula: w_attn = w_attn * (1 + weight) where weight is the feedback value
                result = session.run("""
                    MATCH (n {name: $node_id})-[r]-()
                    SET r.w_attn = coalesce(r.w_attn, 0.0) * (1.0 + $weight),
                        r.ts = timestamp()
                    RETURN count(r) as updated_edges
                """, node_id=payload.node_id, weight=payload.weight)
                
                record = result.single()
                updated_count = record["updated_edges"] if record else 0
                
                return {
                    "status": "accepted",
                    "count": len(feedback_log),
                    "updated_edges": updated_count,
                    "node_id": payload.node_id,
                    "weight": payload.weight
                }
        except Exception as e:
            return {
                "status": "accepted_log_only",
                "count": len(feedback_log),
                "error": str(e),
                "note": "Feedback logged but Neo4j update failed"
            }
    
    return {"status": "accepted", "count": len(feedback_log)}


@app.get("/feedback-log", response_model=List[FeedbackPayload])
def get_feedback_log() -> List[FeedbackPayload]:
    return feedback_log


@app.post("/reset")
def reset_state() -> dict:
    """Reset feedback log and re-seed data."""
    feedback_log.clear()
    
    if not neo4j_driver or not qdrant_client:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database connections not ready")
    
    try:
        from pipeline import initialize_clients, seed_data
        initialize_clients(neo4j_driver, qdrant_client, embedding_model)
        data_file = os.getenv("DATA_FILE", "data/docs-light.jsonl")
        result = seed_data(data_file)
        return {"status": "reset", **result}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@app.post("/switch-dataset")
def switch_dataset(file: str) -> dict:
    """Switch dataset dynamically (similar to kg-no-rag)."""
    if not neo4j_driver or not qdrant_client:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database connections not ready")
    
    # Validate file name
    allowed_files = ["data/docs.jsonl", "data/docs-light.jsonl", "data/docs-50.jsonl", "data/docs-100.jsonl", "data/docs-200.jsonl"]
    if file not in allowed_files:
        return {
            "error": f"Unknown dataset: {file}",
            "available": allowed_files
        }
    
    try:
        from pipeline import initialize_clients, seed_data
        initialize_clients(neo4j_driver, qdrant_client, embedding_model)
        
        # Re-seed data with new file
        result = seed_data(file)
        feedback_log.clear()  # Clear feedback log on dataset switch
        
        return {
            "status": "success",
            "dataset": file,
            "doc_count": result.get("doc_count", 0),
            "message": f"Switched to {file} ({result.get('doc_count', 0)} documents)"
        }
    except FileNotFoundError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"File not found: {file}")
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Switch failed: {str(e)}")


@app.get("/dataset")
def get_dataset() -> dict:
    """Get current dataset information."""
    data_file = os.getenv("DATA_FILE", "data/docs-light.jsonl")
    
    # Count documents
    doc_count = 0
    try:
        if os.path.exists(data_file):
            import json
            with open(data_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        doc_count += 1
    except:
        pass
    
    return {
        "file": data_file,
        "count": doc_count
    }


@app.get("/compare", response_model=CompareResponse)
def compare(question: str, top_k: int = 4, depth: int = 2, theta: float = 0.3):
    """Execute same question on GraphRAG and LightRAG, and return diff."""
    # GraphRAG HTTP call
    import httpx
    try:
        gr_resp = httpx.post(
            "http://graphrag:8000/ask",
            json={
                "question": question,
                "graph_walk": {"max_depth": depth + 1, "prune_threshold": 0.2},
            },
            timeout=20.0,
        )
        gr_data = gr_resp.json()
    except Exception as e:
        gr_data = {"error": f"GraphRAG request failed: {e}"}

    # LightRAG internal call
    from pipeline import query_lightrag
    try:
        lr_data = query_lightrag(question=question, top_k=max(top_k, 6), depth=depth, theta=theta)
        # shape to API-like
        lr_api = {
            "answer": lr_data.get("answer"),
            "graph_nodes": [n.get("name") for n in lr_data.get("graph_nodes", [])],
            "metadata": lr_data.get("metadata", {}),
        }
    except Exception as e:
        lr_api = {"error": f"LightRAG query failed: {e}"}

    diffs = _calc_differences(gr_data, lr_api)
    return CompareResponse(question=question, graphrag=gr_data, lightrag=lr_api, differences=diffs)


@app.get("/eval")
def eval_all() -> dict:
    """Run predefined questions and summarize results for both systems."""
    import json as _json
    import httpx
    questions_path = os.getenv("QUESTIONS_FILE", "questions.json")
    try:
        with open(questions_path, "r", encoding="utf-8") as f:
            qs = _json.load(f)
    except Exception as e:
        return {"error": f"failed to read questions.json: {e}"}

    results = []
    ok_gr = ok_lr = 0
    for it in qs:
        q = it.get("ask")
        expected = set(it.get("expected", []))

        # GraphRAG
        try:
            gr = httpx.post(
                "http://graphrag:8000/ask",
                json={"question": q, "graph_walk": {"max_depth": 3, "prune_threshold": 0.2}},
                timeout=20.0,
            ).json()
            gr_nodes = set(gr.get("metadata", {}).get("graph_nodes", []) or gr.get("graph_nodes", []) or [])
        except Exception:
            gr_nodes = set()

        # LightRAG (internal)
        from pipeline import query_lightrag
        try:
            lr = query_lightrag(question=q, top_k=6, depth=2, theta=0.3)
            lr_nodes = set([n.get("name") for n in lr.get("graph_nodes", [])])
        except Exception:
            lr_nodes = set()

        v_gr = bool(expected) and expected.issubset(gr_nodes) or (not expected and bool(gr_nodes))
        v_lr = bool(expected) and expected.issubset(lr_nodes) or (not expected and bool(lr_nodes))
        ok_gr += int(v_gr); ok_lr += int(v_lr)
        results.append({
            "id": it.get("id"), "ask": q,
            "expected": list(expected),
            "graphrag_nodes": list(gr_nodes),
            "lightrag_nodes": list(lr_nodes),
            "gr_ok": v_gr, "lr_ok": v_lr,
        })

    return {
        "summary": {"graphrag_ok": ok_gr, "lightrag_ok": ok_lr, "total": len(results)},
        "cases": results,
    }
