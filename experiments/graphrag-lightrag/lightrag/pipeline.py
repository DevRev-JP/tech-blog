"""
LightRAG pipeline implementation.
This implements the core LightRAG algorithm with hierarchical retrieval.
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


def initialize_clients(neo4j_drv, qdrant_clt, emb_model=None):
    """Initialize pipeline with database clients and embedding model."""
    global neo4j_driver, qdrant_client, embedding_model
    neo4j_driver = neo4j_drv
    qdrant_client = qdrant_clt
    embedding_model = emb_model


def seed_data(data_file: str = "data/docs-light.jsonl", collection_name: str = "lightrag_docs"):
    """
    Seed data into Qdrant (vector store) and Neo4j (graph store).
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
        # Get embedding dimension from model (384 for all-MiniLM-L6-v2)
        if embedding_model:
            embed_dim = embedding_model.get_sentence_embedding_dimension()
        else:
            embed_dim = 384  # Fallback dimension
        
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=embed_dim, distance=Distance.COSINE)
        )
        print(f"✓ Created Qdrant collection: {collection_name} (dim={embed_dim})")
    
    # Seed Neo4j graph with nodes and edges
    with neo4j_driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        
        # Extract entities and relationships
        for doc in docs:
            doc_id = doc.get("id", "")
            text = doc.get("text", "")
            
            # Extract entities
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
            if "POL-001" in text or "Personal Data Protection" in text:
                policies.append("POL-001")
            if "POL-002" in text or "AI Model Governance" in text:
                policies.append("POL-002")
            
            # Create nodes with text references
            for product in products:
                session.run(
                    """
                    MERGE (p:Product {name: $name})
                    SET p.id = $id, p.text_ref = $text, p.degree = 0
                    """,
                    name=product, id=doc_id, text=text
                )
            
            for feature in features:
                session.run(
                    """
                    MERGE (f:Feature {name: $name})
                    SET f.text_ref = $text, f.degree = 0
                    """,
                    name=feature, text=text
                )
            
            for policy in policies:
                session.run(
                    """
                    MERGE (pol:Policy {name: $name})
                    SET pol.text_ref = $text, pol.degree = 0
                    """,
                    name=policy, text=text
                )
            
            # Create edges with weights
            for product in products:
                for feature in features:
                    session.run(
                        """
                        MATCH (p:Product {name: $product}), (f:Feature {name: $feature})
                        MERGE (p)-[r:HAS_FEATURE]->(f)
                        SET r.w_struct = 1.0, r.w_attn = 0.0, r.ts = timestamp()
                        SET p.degree = p.degree + 1, f.degree = f.degree + 1
                        """,
                        product=product, feature=feature
                    )
            
            # Create REGULATES relationships (Feature -> Policy)
            # Policy Audit can check POL-001 and POL-002
            if "Policy Audit" in features:
                for policy in policies:
                    session.run(
                        """
                        MATCH (f:Feature {name: 'Policy Audit'}), (pol:Policy {name: $policy})
                        MERGE (f)-[r:REGULATES]->(pol)
                        SET r.w_struct = 1.0, r.w_attn = 0.0, r.ts = timestamp()
                        SET f.degree = f.degree + 1, pol.degree = pol.degree + 1
                        """,
                        policy=policy
                    )
        
        # Calculate initial centrality (simplified)
        session.run("""
            MATCH (n)
            SET n.centrality = n.degree
        """)
        
        print(f"✓ Seeded {len(docs)} documents to Neo4j")
    
    # Seed Qdrant with embeddings if model is available
    if embedding_model and qdrant_client:
        points = []
        for i, doc in enumerate(docs):
            doc_id = doc.get("id", f"doc_{i}")
            text = doc.get("text", "")
            
            # Generate embedding
            embedding = embedding_model.encode(text).tolist()
            
            points.append(PointStruct(
                id=i,
                vector=embedding,
                payload={
                    "id": doc_id,
                    "text": text
                }
            ))
        
        if points:
            qdrant_client.upsert(collection_name=collection_name, points=points)
            print(f"✓ Seeded {len(points)} embeddings to Qdrant")
    
    return {"status": "success", "doc_count": len(docs)}


def build_local_graph(
    seed_nodes: List[str],
    max_depth: int = 2,
    theta: float = 0.3,
    collection_name: str = "lightrag_docs"
) -> Dict:
    """
    Build local subgraph from seed nodes (LightRAG's graph-level retrieval).
    Returns nodes with their beta scores (graph-level scores).
    """
    if not neo4j_driver:
        raise RuntimeError("Neo4j driver not initialized")
    
    visited = set(seed_nodes)
    frontier = list(seed_nodes)
    all_nodes = set(seed_nodes)
    beta_scores = {}  # Track beta scores (graph-level) for each node
    
    # Initialize seed nodes with beta score = 1.0
    for node_name in seed_nodes:
        beta_scores[node_name] = 1.0
    
    max_depth_reached = 0
    for depth in range(max_depth):
        new_frontier = []
        
        with neo4j_driver.session() as session:
            for node_name in frontier:
                # Get neighbors with scoring
                result = session.run("""
                    MATCH (n {name: $name})-[r]-(neighbor)
                    WHERE NOT neighbor.name IN $visited
                    RETURN 
                        neighbor.name as name,
                        labels(neighbor)[0] as type,
                        type(r) as rel_type,
                        coalesce(r.w_struct, 1.0) * (1.0 + coalesce(r.w_attn, 0.0)) as score,
                        neighbor.centrality as centrality
                    ORDER BY score DESC
                    LIMIT 5
                """, name=node_name, visited=list(visited))
                
                for record in result:
                    neighbor_name = record["name"]
                    graph_score = record["score"]  # This is beta (graph-level score)
                    
                    if neighbor_name not in visited and graph_score >= theta:
                        visited.add(neighbor_name)
                        all_nodes.add(neighbor_name)
                        # Store beta score (graph-level score)
                        # Use the graph score directly, or combine with parent's beta if available
                        parent_beta = beta_scores.get(node_name, 1.0)
                        beta_scores[neighbor_name] = graph_score * parent_beta  # Simplified: multiply parent beta
                        new_frontier.append(neighbor_name)
        
        max_depth_reached = depth + 1
        frontier = new_frontier
        if not new_frontier:
            break
    
    return {
        "nodes": list(all_nodes),
        "visited_count": len(visited),
        "max_depth_reached": max_depth_reached,
        "beta_scores": beta_scores  # Return beta scores for integration
    }


def query_lightrag(
    question: str,
    top_k: int = 4,
    depth: int = 2,
    theta: float = 0.3,
    collection_name: str = "lightrag_docs"
) -> Dict:
    """
    Execute LightRAG query with hierarchical retrieval.
    
    Steps:
    1. Vector-level retrieval: Find top-k documents
    2. Graph-level retrieval: Build local subgraph from seed nodes
    3. Score integration: Combine vector scores and graph scores
    4. Context compression: Select top nodes by importance
    """
    if not qdrant_client or not neo4j_driver:
        raise RuntimeError("Clients not initialized")
    
    # Step 1: Vector-level retrieval (low-level) - get alpha scores
    alpha_scores = {}  # Vector-level scores (low-level)
    seed_nodes = []
    
    if embedding_model and qdrant_client:
        # Generate query embedding
        query_vector = embedding_model.encode(question).tolist()
        
        # Search Qdrant for top-k similar documents
        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k * 2  # Get more results to extract nodes
        )
        
        # Extract seed nodes from retrieved documents with alpha scores
        node_to_alpha = {}  # Map node name to its best alpha score
        for result in search_results:
            payload = result.payload or {}
            text = payload.get("text", "")
            score = result.score  # This is the vector similarity score (alpha)
            
            # Extract entities from retrieved text and assign alpha scores
            entities_found = []
            if "Acme Search" in text:
                entities_found.append("Acme Search")
            if "Globex Graph" in text:
                entities_found.append("Globex Graph")
            if "Semantic Index" in text:
                entities_found.append("Semantic Index")
            if "Policy Audit" in text:
                entities_found.append("Policy Audit")
            if "Realtime Query" in text:
                entities_found.append("Realtime Query")
            if "POL-001" in text or "Personal Data Protection" in text:
                entities_found.append("POL-001")
            if "POL-002" in text or "AI Model Governance" in text:
                entities_found.append("POL-002")
            
            # Assign alpha score to each entity (use max if entity appears multiple times)
            for entity in entities_found:
                if entity not in node_to_alpha or score > node_to_alpha[entity]:
                    node_to_alpha[entity] = score
        
        # Normalize alpha scores to [0, 1] range (min-max normalization)
        if node_to_alpha:
            max_alpha = max(node_to_alpha.values())
            min_alpha = min(node_to_alpha.values())
            alpha_range = max_alpha - min_alpha if max_alpha > min_alpha else 1.0
            
            for node_name, raw_score in node_to_alpha.items():
                normalized_alpha = (raw_score - min_alpha) / alpha_range if alpha_range > 0 else 1.0
                alpha_scores[node_name] = normalized_alpha
                seed_nodes.append(node_name)
        
    else:
        # Fallback: use keyword matching if embedding model not available
        if "Acme Search" in question or "Acme" in question:
            seed_nodes.append("Acme Search")
            alpha_scores["Acme Search"] = 1.0
        if "Globex Graph" in question or "Globex" in question:
            seed_nodes.append("Globex Graph")
            alpha_scores["Globex Graph"] = 1.0
        if "Semantic Index" in question:
            seed_nodes.append("Semantic Index")
            alpha_scores["Semantic Index"] = 1.0
        if "Policy Audit" in question:
            seed_nodes.append("Policy Audit")
            alpha_scores["Policy Audit"] = 1.0
        if "Realtime Query" in question:
            seed_nodes.append("Realtime Query")
            alpha_scores["Realtime Query"] = 1.0
        
        if not seed_nodes:
            # Final fallback: get all products from Neo4j
            with neo4j_driver.session() as session:
                result = session.run("MATCH (p:Product) RETURN p.name as name LIMIT 3")
                seed_nodes = [r["name"] for r in result]
                for node_name in seed_nodes:
                    alpha_scores[node_name] = 0.5  # Default alpha for fallback nodes
    
    # Step 2: Graph-level retrieval (high-level) - build local subgraph and get beta scores
    try:
        subgraph = build_local_graph(seed_nodes, max_depth=depth, theta=theta)
        beta_scores = subgraph.get("beta_scores", {})  # Beta scores (graph-level)
    except Exception as e:
        # Fallback if subgraph building fails
        print(f"⚠ build_local_graph failed: {e}")
        subgraph = {"visited_count": len(seed_nodes), "max_depth_reached": 0, "beta_scores": {}}
        beta_scores = {}
    
    # Step 3: Score integration - combine alpha and beta with 0.6/0.4 ratio
    # final_score = alpha * 0.6 + beta * 0.4
    final_scores = {}
    all_node_names = set(alpha_scores.keys()) | set(beta_scores.keys())
    
    for node_name in all_node_names:
        alpha = alpha_scores.get(node_name, 0.0)
        beta = beta_scores.get(node_name, 0.0)
        # Normalize beta to [0, 1] if needed (beta_scores might be > 1)
        if beta > 0:
            # Normalize beta: assume max beta is around 2-3, normalize to [0, 1]
            normalized_beta = min(beta / 3.0, 1.0) if beta > 1.0 else beta
        else:
            normalized_beta = 0.0
        
        final_score = alpha * 0.6 + normalized_beta * 0.4
        final_scores[node_name] = final_score
    
    # Sort nodes by final score and select top_k
    ranked_nodes = sorted(all_node_names, key=lambda n: final_scores.get(n, 0.0), reverse=True)
    node_names = ranked_nodes[:top_k]
    
    # Step 4: Context compression - build answer from top nodes
    with neo4j_driver.session() as session:
        
        if not node_names:
            answer = "関連する情報が見つかりませんでした。"
            nodes = []
        else:
            # Build answer from graph context
            result = session.run("""
                MATCH (n)
                WHERE n.name IN $names
                OPTIONAL MATCH (n)-[r]-(related)
                RETURN 
                    n.name as name,
                    labels(n)[0] as type,
                    collect(DISTINCT related.name) as related
                LIMIT $limit
            """, names=node_names, limit=top_k)
            
            nodes_info = []
            answer_parts = []
            
            for record in result:
                name = record["name"]
                node_type = record["type"] or "Unknown"
                related = [r for r in record["related"] if r]
                
                nodes_info.append({
                    "name": name,
                    "type": node_type,
                    "related": related
                })
                
                if related:
                    answer_parts.append(f"{name} ({node_type}) は {', '.join(related[:3])} と関連しています。")
                else:
                    answer_parts.append(f"{name} ({node_type}) が見つかりました。")
            
            answer = "\n".join(answer_parts) if answer_parts else "情報を取得しました。"
            nodes = [{"name": n["name"], "type": n["type"]} for n in nodes_info]
    
    # Build subgraph metadata safely
    subgraph_metadata = None
    if subgraph and isinstance(subgraph, dict):
        try:
            subgraph_metadata = {
            "total_nodes": subgraph.get("visited_count", len(seed_nodes)),
            "depth": subgraph.get("max_depth_reached", 0)
        }
        except (KeyError, TypeError):
            subgraph_metadata = {
                "total_nodes": len(seed_nodes),
                "depth": 0
            }
    
    return {
        "answer": answer,
        "vector_nodes": seed_nodes[:top_k],
        "graph_nodes": nodes,
        "subgraph": subgraph_metadata,
        "metadata": {
            "top_k": top_k,
            "depth": depth,
            "theta": theta,
            "alpha_beta_ratio": "0.6/0.4",
            "final_scores": {n: round(final_scores.get(n, 0.0), 3) for n in node_names[:top_k]},
            "pipeline": "lightrag-simplified"
        }
    }

