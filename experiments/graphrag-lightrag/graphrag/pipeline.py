"""
GraphRAG pipeline implementation (simplified version).
This is a placeholder implementation that mimics GraphRAG behavior.
In production, this would use the actual Microsoft GraphRAG CLI.
"""
import os
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from neo4j import GraphDatabase

# Global clients (initialized from main.py)
neo4j_driver = None
qdrant_client = None
embedding_model = None


def initialize_clients(neo4j_drv, qdrant_clt):
    """Initialize pipeline with database clients."""
    global neo4j_driver, qdrant_client
    neo4j_driver = neo4j_drv
    qdrant_client = qdrant_clt


def seed_data(data_file: str = "data/docs-light.jsonl", collection_name: str = "graphrag_docs"):
    """
    Seed data into Qdrant and Neo4j.
    This is a simplified version - in production, GraphRAG CLI would handle this.
    """
    import json
    
    if not qdrant_client or not neo4j_driver:
        raise RuntimeError("Clients not initialized")
    
    # Read data
    docs = []
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    docs.append(json.loads(line))
    
    if not docs:
        print(f"⚠ No data found in {data_file}")
        return {"status": "no_data"}
    
    # Create Qdrant collection if needed
    collections = qdrant_client.get_collections().collections
    collection_exists = any(c.name == collection_name for c in collections)
    
    if not collection_exists:
        # Use dummy embedding dimension (384 for all-MiniLM-L6-v2)
        # In production, GraphRAG would use the actual embedding model
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print(f"✓ Created Qdrant collection: {collection_name}")
    
    # Seed Neo4j graph (simplified - extract entities and relationships)
    with neo4j_driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        
        # Extract simple entities and relationships from text
        for doc in docs:
            doc_id = doc.get("id", "")
            text = doc.get("text", "")
            
            # Simple entity extraction (product names, policy names, features)
            products = []
            if "Acme Search" in text:
                products.append("Acme Search")
            if "Globex Graph" in text:
                products.append("Globex Graph")
            
            features = []
            if "Semantic Index" in text:
                features.append("Semantic Index")
            if "Policy Audit" in text:
                features.append("Policy Audit")
            if "Realtime Query" in text:
                features.append("Realtime Query")
            
            policies = []
            if "POL-001" in text:
                policies.append("POL-001")
            if "POL-002" in text:
                policies.append("POL-002")
            
            # Create nodes and relationships
            for product in products:
                session.run(
                    "MERGE (p:Product {name: $name}) SET p.id = $id",
                    name=product, id=doc_id
                )
            
            for feature in features:
                session.run(
                    "MERGE (f:Feature {name: $name})",
                    name=feature
                )
            
            for policy in policies:
                session.run(
                    "MERGE (pol:Policy {name: $name})",
                    name=policy
                )
            
            # Create relationships
            for product in products:
                for feature in features:
                    session.run(
                        "MATCH (p:Product {name: $product}), (f:Feature {name: $feature}) "
                        "MERGE (p)-[:HAS_FEATURE]->(f)",
                        product=product, feature=feature
                    )
            
            # Create REGULATES relationships (Feature -> Policy)
            # Policy Audit can check POL-001 and POL-002
            if "Policy Audit" in features:
                for policy in policies:
                    session.run(
                        "MATCH (f:Feature {name: 'Policy Audit'}), (pol:Policy {name: $policy}) "
                        "MERGE (f)-[:REGULATES]->(pol)",
                        policy=policy
                    )
        
        print(f"✓ Seeded {len(docs)} documents to Neo4j")
    
    return {"status": "success", "doc_count": len(docs)}


def query_graph(
    question: str,
    max_depth: int = 3,
    prune_threshold: float = 0.2,
    collection_name: str = "graphrag_docs"
) -> Dict:
    """
    Query GraphRAG pipeline with graph walk using max_depth and prune_threshold.
    """
    if not qdrant_client or not neo4j_driver:
        raise RuntimeError("Clients not initialized")
    
    # Step 1: Find seed nodes from question keywords
    seed_nodes = []
    if "Acme Search" in question or "Acme" in question:
        seed_nodes.append("Acme Search")
    if "Globex Graph" in question or "Globex" in question:
        seed_nodes.append("Globex Graph")
    if "Semantic Index" in question:
        seed_nodes.append("Semantic Index")
    if "Policy Audit" in question:
        seed_nodes.append("Policy Audit")
    if "POL-001" in question:
        seed_nodes.append("POL-001")
    if "POL-002" in question:
        seed_nodes.append("POL-002")
    
    if not seed_nodes:
        # Fallback: get all products if no keywords found
        with neo4j_driver.session() as session:
            result = session.run("MATCH (p:Product) RETURN p.name as name LIMIT 3")
            seed_nodes = [r["name"] for r in result]
    
    # Step 2: Graph walk with max_depth and prune_threshold
    visited = set(seed_nodes)
    frontier = list(seed_nodes)
    all_nodes = set(seed_nodes)
    node_scores = {}  # Track scores for pruning
    
    with neo4j_driver.session() as session:
        # Initialize seed node scores
        for node_name in seed_nodes:
            node_scores[node_name] = 1.0
        
        # Perform graph walk up to max_depth
        for depth in range(max_depth):
            new_frontier = []
            
            for node_name in frontier:
                # Get neighbors with relationship information
                result = session.run("""
                    MATCH (n {name: $name})-[r]-(neighbor)
                    WHERE NOT neighbor.name IN $visited
                    RETURN 
                        neighbor.name as name,
                        labels(neighbor)[0] as type,
                        type(r) as rel_type,
                        coalesce(r.w_struct, 1.0) as edge_weight
                """, name=node_name, visited=list(visited))
                
                for record in result:
                    neighbor_name = record["name"]
                    if neighbor_name not in visited:
                        # Calculate score: parent score * edge weight (simplified scoring)
                        edge_weight = record["edge_weight"] or 1.0
                        parent_score = node_scores.get(node_name, 1.0)
                        neighbor_score = parent_score * edge_weight
                        
                        # Prune based on threshold
                        if neighbor_score >= prune_threshold:
                            visited.add(neighbor_name)
                            all_nodes.add(neighbor_name)
                            node_scores[neighbor_name] = neighbor_score
                            new_frontier.append(neighbor_name)
            
            frontier = new_frontier
            if not new_frontier:
                break
        
        # Build nodes list with scores
        nodes = []
        for node_name in sorted(all_nodes, key=lambda n: node_scores.get(n, 0.0), reverse=True):
            # Get node type and related info
            result = session.run("""
                MATCH (n {name: $name})
                OPTIONAL MATCH (n)-[r]-(related)
                RETURN 
                    labels(n)[0] as type,
                    collect(DISTINCT related.name) as related
                LIMIT 1
            """, name=node_name)
            
            record = result.single()
            node_type = record["type"] if record else "Unknown"
            related = [r for r in (record["related"] if record else []) if r]
            
            nodes.append({
                "name": node_name,
                "type": node_type,
                "score": node_scores.get(node_name, 0.0),
                "related": related[:3]  # Limit related nodes
            })
        
        # Build answer
        if "product" in question.lower() or "製品" in question:
            product_nodes = [n for n in nodes if n["type"] == "Product"]
            if product_nodes:
                answer = f"製品一覧: {', '.join([n['name'] for n in product_nodes])}"
            else:
                answer = f"検索結果: {', '.join([n['name'] for n in nodes[:5]])}"
        elif "policy" in question.lower() or "ポリシー" in question or "政策" in question:
            policy_nodes = [n for n in nodes if n["type"] == "Policy"]
            if policy_nodes:
                answer = f"関連ポリシー: {', '.join([n['name'] for n in policy_nodes])}"
            else:
                answer = f"検索結果: {', '.join([n['name'] for n in nodes[:5]])}"
        else:
            # Default: show top nodes with relationships
            top_answer_nodes = nodes[:5]
            if top_answer_nodes:
                answer_parts = []
                for node in top_answer_nodes:
                    if node["related"]:
                        answer_parts.append(f"{node['name']} ({node['type']}) は {', '.join(node['related'])} と関連")
                    else:
                        answer_parts.append(f"{node['name']} ({node['type']})")
                answer = "製品と機能の関係:\n" + "\n".join(answer_parts)
            else:
                answer = f"検索結果: {', '.join([n['name'] for n in nodes[:5]])}"
    
    # Limit returned nodes to top ones by score
    # GraphRAG typically explores many nodes, but for fair comparison with LightRAG
    # we limit the returned nodes to top-scoring ones (similar to LightRAG's top_k)
    top_returned_nodes = sorted(nodes, key=lambda n: n["score"], reverse=True)[:6]  # Limit to top 6 (similar to LightRAG)
    
    return {
        "answer": answer,
        "graph_nodes": [{"name": n["name"], "type": n["type"]} for n in top_returned_nodes],
        "metadata": {
            "max_depth": max_depth,
            "prune_threshold": prune_threshold,
            "nodes_explored": len(all_nodes),
            "nodes_returned": len(top_returned_nodes),
            "actual_depth": depth + 1 if frontier else depth,
            "pipeline": "graphrag-simplified"
        }
    }


