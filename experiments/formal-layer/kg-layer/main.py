import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from neo4j import GraphDatabase

# Neo4j driver (initialized on startup)
neo4j_driver = None

app = FastAPI(title="KG Layer API", version="1.0.0")


class QueryRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID to query")
    path_type: Optional[str] = Field(
        None, description="Path type: 'sla', 'contract', 'plan', or 'full' (all paths)"
    )


class QueryResponse(BaseModel):
    customer_id: str
    results: List[Dict[str, Any]]
    query_used: str


@app.on_event("startup")
async def startup_event():
    """Initialize Neo4j connection and seed data."""
    global neo4j_driver
    
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        neo4j_driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )
        # Test connection
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        
        # Seed sample data
        seed_data()
        print("✅ Neo4j connected and data seeded")
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        raise


def seed_data():
    """Seed sample knowledge graph data."""
    with neo4j_driver.session() as session:
        # Clear existing sample data for this experiment only
        # ※ 専用の Neo4j コンテナ内での利用を前提とし、ラベルベースで削除しています。
        session.run("""
            MATCH (n)
            WHERE n:Customer OR n:Contract OR n:Plan OR n:SLA
            DETACH DELETE n
        """)
        
        # Create sample graph: Customer -> Contract -> Plan -> SLA
        session.run("""
            CREATE (c1:Customer {id: "CUST-123"})
            CREATE (c2:Customer {id: "CUST-456"})
            CREATE (con1:Contract {id: "CON-1", plan_name: "Enterprise"})
            CREATE (con2:Contract {id: "CON-2", plan_name: "Standard"})
            CREATE (p1:Plan {name: "Enterprise"})
            CREATE (p2:Plan {name: "Standard"})
            CREATE (sla1:SLA {priority: "High", response_time: "1 hour"})
            CREATE (sla2:SLA {priority: "Medium", response_time: "4 hours"})
            
            CREATE (c1)-[:HAS_CONTRACT]->(con1)
            CREATE (c2)-[:HAS_CONTRACT]->(con2)
            CREATE (con1)-[:ON_PLAN]->(p1)
            CREATE (con2)-[:ON_PLAN]->(p2)
            CREATE (p1)-[:HAS_SLA]->(sla1)
            CREATE (p2)-[:HAS_SLA]->(sla2)
        """)


@app.on_event("shutdown")
async def shutdown_event():
    """Close Neo4j connection."""
    global neo4j_driver
    if neo4j_driver:
        neo4j_driver.close()


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    try:
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        return {"status": "ok", "service": "kg-layer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/paths")
async def get_paths():
    """
    Get available path templates.
    
    Returns a list of path templates that can be used for querying the knowledge graph.
    LLM can select from these templates based on natural language input.
    """
    paths = [
        {
            "path_type": "sla",
            "description": "Customer -> Contract -> Plan -> SLA",
            "returns": "SLA priority and response time",
            "use_case": "Get SLA information for a customer"
        },
        {
            "path_type": "contract",
            "description": "Customer -> Contract",
            "returns": "Contract information",
            "use_case": "Get contract details for a customer"
        },
        {
            "path_type": "plan",
            "description": "Customer -> Contract -> Plan",
            "returns": "Plan information",
            "use_case": "Get plan details for a customer"
        },
        {
            "path_type": "full",
            "description": "Customer -> Contract -> Plan -> SLA (all paths)",
            "returns": "All information along the path",
            "use_case": "Get complete customer information"
        }
    ]
    return {"paths": paths}


@app.post("/query", response_model=QueryResponse)
async def query_kg(request: QueryRequest):
    """
    Query the knowledge graph.
    
    Example: Query SLA priority for a customer through the path:
    Customer -> Contract -> Plan -> SLA
    """
    if not neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j not connected")
    
    try:
        params = {"customer_id": request.customer_id}
        
        if request.path_type == "sla":
            # Query SLA priority through the full path
            query = """
                MATCH (c:Customer {id: $customer_id})
                  -[:HAS_CONTRACT]->(:Contract)
                  -[:ON_PLAN]->(:Plan)
                  -[:HAS_SLA]->(s:SLA)
                RETURN s.priority as priority, s.response_time as response_time
            """
        elif request.path_type == "contract":
            # Query contract information only
            query = """
                MATCH (c:Customer {id: $customer_id})
                  -[:HAS_CONTRACT]->(con:Contract)
                RETURN c.id as customer_id, con.id as contract_id, 
                       con.plan_name as plan_name
            """
        elif request.path_type == "plan":
            # Query plan information
            query = """
                MATCH (c:Customer {id: $customer_id})
                  -[:HAS_CONTRACT]->(:Contract)
                  -[:ON_PLAN]->(p:Plan)
                RETURN c.id as customer_id, p.name as plan_name
            """
        else:
            # Query all paths from customer (full or None)
            query = """
                MATCH (c:Customer {id: $customer_id})
                  -[:HAS_CONTRACT]->(con:Contract)
                  -[:ON_PLAN]->(p:Plan)
                  -[:HAS_SLA]->(s:SLA)
                RETURN c.id as customer_id, con.id as contract_id, 
                       p.name as plan_name, s.priority as sla_priority,
                       s.response_time as response_time
            """
        
        with neo4j_driver.session() as session:
            result = session.run(query, params)
            records = [dict(record) for record in result]
        
        return QueryResponse(
            customer_id=request.customer_id,
            results=records,
            query_used=query.strip()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph")
async def get_graph():
    """Get the entire graph structure (for visualization)."""
    if not neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j not connected")
    
    try:
        query = """
            MATCH (c:Customer)-[:HAS_CONTRACT]->(con:Contract)
                  -[:ON_PLAN]->(p:Plan)
                  -[:HAS_SLA]->(s:SLA)
            RETURN c.id as customer_id, con.id as contract_id,
                   p.name as plan_name, s.priority as sla_priority
        """
        
        with neo4j_driver.session() as session:
            result = session.run(query)
            records = [dict(record) for record in result]
        
        return {"graph": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

