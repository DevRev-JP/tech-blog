import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Database clients (initialized on startup)
neo4j_driver = None
qdrant_client = None


class GraphWalkParams(BaseModel):
    max_depth: int = Field(3, ge=1, description="Number of hops for graph traversal")
    prune_threshold: float = Field(
        0.2,
        ge=0,
        le=1,
        description="Threshold for pruning low-scoring nodes",
    )


class AskRequest(BaseModel):
    question: str = Field(..., description="Natural language question to evaluate")
    graph_walk: Optional[GraphWalkParams] = Field(
        default=None,
        description="GraphRAG traversal parameters (optional in stub implementation)",
    )


class AskResponse(BaseModel):
    answer: str
    metadata: dict


app = FastAPI(title="GraphRAG API", version="0.1.0")


@app.on_event("startup")
async def startup_event():
    """Initialize database connections and seed data on startup."""
    global neo4j_driver, qdrant_client
    
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
    
    # Initialize pipeline and seed data if clients are ready
    if neo4j_driver and qdrant_client:
        try:
            from pipeline import initialize_clients, seed_data
            initialize_clients(neo4j_driver, qdrant_client)
            data_file = os.getenv("DATA_FILE", "data/docs-light.jsonl")
            result = seed_data(data_file)
            print(f"✓ Data seeding: {result.get('status')}")
        except Exception as e:
            print(f"⚠ Data seeding failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown."""
    global neo4j_driver, qdrant_client
    if neo4j_driver:
        neo4j_driver.close()
        print("✓ Neo4j connection closed")


@app.get("/healthz")
def healthcheck() -> dict:
    """Lightweight readiness endpoint with DB connection status."""
    status = {
        "status": "ok",
        "service": "graphrag-api",
        "version": app.version,
        "connections": {
            "neo4j": neo4j_driver is not None,
            "qdrant": qdrant_client is not None,
        },
    }
    return status


@app.get("/connections")
def check_connections() -> dict:
    """Check database connections and return detailed status."""
    result = {
        "neo4j": {"connected": False, "error": None},
        "qdrant": {"connected": False, "error": None},
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
def ask_question(payload: AskRequest) -> AskResponse:
    """Query GraphRAG pipeline."""
    graph_walk = payload.graph_walk or GraphWalkParams()
    
    if not neo4j_driver or not qdrant_client:
        raise HTTPException(
            status_code=503,
            detail="Database connections not ready"
        )
    
    try:
        from pipeline import query_graph
        result = query_graph(
            question=payload.question,
            max_depth=graph_walk.max_depth,
            prune_threshold=graph_walk.prune_threshold
        )
        
        metadata = {
            "question": payload.question,
            "graph_walk": graph_walk.model_dump(),
            **result.get("metadata", {})
        }
        
        # Include graph_nodes in metadata for evaluation
        graph_nodes = result.get("graph_nodes", [])
        metadata["graph_nodes"] = [n.get("name") if isinstance(n, dict) else n for n in graph_nodes]
        
        return AskResponse(
            answer=result.get("answer", "No answer generated"),
            metadata=metadata
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@app.post("/reset")
def reset_data() -> dict:
    """Reset and re-seed data."""
    if not neo4j_driver or not qdrant_client:
        raise HTTPException(status_code=503, detail="Database connections not ready")
    
    try:
        from pipeline import seed_data
        data_file = os.getenv("DATA_FILE", "data/docs-light.jsonl")
        result = seed_data(data_file)
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@app.post("/switch-dataset")
def switch_dataset(file: str) -> dict:
    """Switch dataset dynamically (similar to kg-no-rag)."""
    if not neo4j_driver or not qdrant_client:
        raise HTTPException(status_code=503, detail="Database connections not ready")
    
    # Validate file name
    allowed_files = ["data/docs.jsonl", "data/docs-light.jsonl", "data/docs-50.jsonl"]
    if file not in allowed_files:
        return {
            "error": f"Unknown dataset: {file}",
            "available": allowed_files
        }
    
    try:
        from pipeline import seed_data
        
        # Re-seed data with new file
        result = seed_data(file)
        
        return {
            "status": "success",
            "dataset": file,
            "doc_count": result.get("doc_count", 0),
            "message": f"Switched to {file} ({result.get('doc_count', 0)} documents)"
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file}")
    except Exception as e:
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
