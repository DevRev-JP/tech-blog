"""
LightRAG pipeline implementation.
This implements the core LightRAG algorithm with hierarchical retrieval.
"""
import os
import re
from typing import List, Dict, Optional, Set
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from neo4j import GraphDatabase

# Global clients (initialized from main.py)
neo4j_driver = None
qdrant_client = None
embedding_model = None


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract entities (products, features, policies) from text using pattern matching.
    This is a simplified NER implementation for demonstration purposes.
    """
    entities = {
        "products": [],
        "features": [],
        "policies": []
    }
    
    # Known products and features that should be prioritized (extract first)
    known_products = ["Acme Search", "Globex Graph"]
    known_features = ["Semantic Index", "Policy Audit", "Realtime Query"]
    
    for known_product in known_products:
        if known_product in text and known_product not in entities["products"]:
            entities["products"].append(known_product)
    
    for known_feature in known_features:
        if known_feature in text and known_feature not in entities["features"]:
            entities["features"].append(known_feature)
    
    # Product patterns: "Name Platform", "Name Pro", "Name Suite", "Name Manager", etc.
    # Also includes known products like "Acme Search", "Globex Graph"
    # Exclude known features from product patterns
    product_patterns = [
        r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\s+(?:Platform|Pro|Suite|Manager|Engine|System|Tool|Service|Core|Hub|Framework|Studio|Builder)\b',
        r'\b([A-Z][a-zA-Z]+\s+(?:Search|Graph|Vault|Guard|Bridge|Optimizer|Collector|Analyzer|Scanner|Delivery|Campaign|Bot))\b',  # Removed Index from this pattern
        r'\b(Acme\s+Search|Globex\s+Graph|CloudBridge\s+Platform|DataVault\s+Pro|NetworkGuard\s+Suite)\b',
        # Also match standalone product names that appear in "Product Name は" pattern
        r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+は'
    ]
    
    for pattern in product_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            product_name = match if isinstance(match, str) else match[0] if isinstance(match, tuple) else str(match)
            product_name = product_name.strip()
            # Filter out common Japanese words, policy names, and known features
            if (len(product_name) > 3 and 
                product_name not in ["POL-001", "POL-002", "Personal", "Data", "Protection", "Model", "Governance"] and
                product_name not in entities["products"] and
                product_name not in entities["features"]):  # Don't add if already identified as a feature
                entities["products"].append(product_name)
    
    # Feature patterns: "Feature Name" (typically capitalized words)
    feature_patterns = [
        r'\b(Semantic\s+Index|Policy\s+Audit|Realtime\s+Query)\b',  # Known features (already added above, but keep for consistency)
        r'\b([A-Z][a-zA-Z]+\s+(?:Index|Query|Audit|Engine|Manager|Optimizer|Analyzer|Scanner|Framework|Builder))\b',
        # Features that appear after "機能" or "を提供" or "を搭載"
        r'(?:機能|を提供|を搭載)[する]?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)'
    ]
    
    for pattern in feature_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            feature_name = match if isinstance(match, str) else match[0] if isinstance(match, tuple) else str(match)
            feature_name = feature_name.strip()
            if (len(feature_name) > 3 and 
                feature_name not in entities["features"] and
                feature_name not in entities["products"]):  # Avoid duplicates
                entities["features"].append(feature_name)
    
    # Policy patterns: POL-XXX or "Policy Name (POL-XXX)"
    policy_patterns = [
        r'\bPOL-(\d+)\b',
        r'\(POL-(\d+)\)',
        r'\b(Personal\s+Data\s+Protection|AI\s+Model\s+Governance)\b'
    ]
    
    for pattern in policy_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match else ""
            policy_id = f"POL-{match}" if match.isdigit() else match
            policy_id = policy_id.strip()
            if policy_id and policy_id not in entities["policies"]:
                entities["policies"].append(policy_id)
    
    return entities


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
        
        # Extract entities and relationships from text
        # Collect all unique entities across all documents
        all_products = set()
        all_features = set()
        all_policies = set()
        
        for doc in docs:
            doc_id = doc.get("id", "")
            text = doc.get("text", "")
            
            # Extract entities using improved pattern matching
            entities = extract_entities(text)
            all_products.update(entities["products"])
            all_features.update(entities["features"])
            all_policies.update(entities["policies"])
        
        print(f"✓ Extracted entities: {len(all_products)} products, {len(all_features)} features, {len(all_policies)} policies")
        
        # Create all nodes first
        for product in all_products:
            session.run(
                """
                MERGE (p:Product {name: $name})
                SET p.text_ref = $text, p.degree = 0, p.created_from = 'auto_extract'
                """,
                name=product, text=""
            )
        
        for feature in all_features:
            session.run(
                """
                MERGE (f:Feature {name: $name})
                SET f.text_ref = $text, f.degree = 0, f.created_from = 'auto_extract'
                """,
                name=feature, text=""
            )
        
        for policy in all_policies:
            session.run(
                """
                MERGE (pol:Policy {name: $name})
                SET pol.text_ref = $text, pol.degree = 0, pol.created_from = 'auto_extract'
                """,
                name=policy, text=""
            )
        
        # Extract relationships from documents
        for doc in docs:
            doc_id = doc.get("id", "")
            text = doc.get("text", "")
            
            # Extract entities for this document
            entities = extract_entities(text)
            products = entities["products"]
            features = entities["features"]
            policies = entities["policies"]
            
            # Create relationships (nodes already created above)
            # Product-Feature relationships
            for product in products:
                for feature in features:
                    session.run(
                        """
                        MATCH (p:Product {name: $product}), (f:Feature {name: $feature})
                        MERGE (p)-[r:HAS_FEATURE]->(f)
                        SET r.w_struct = 1.0, r.w_attn = 0.0, r.ts = timestamp()
                        SET p.degree = p.degree + 1, f.degree = f.degree + 1
                        SET p.doc_ref = $doc_id
                        """,
                        product=product, feature=feature, doc_id=doc_id
                    )
            
            # Feature-Policy relationships (any feature that mentions a policy)
            # Also create if text mentions "Policy" near a feature
            if "Policy" in text or any("Policy" in f or "POL" in p for f in features for p in policies):
                for feature in features:
                    for policy in policies:
                        session.run(
                            """
                            MATCH (f:Feature {name: $feature}), (pol:Policy {name: $policy})
                            MERGE (f)-[r:REGULATES]->(pol)
                            SET r.w_struct = 1.0, r.w_attn = 0.0, r.ts = timestamp()
                            SET f.degree = f.degree + 1, pol.degree = pol.degree + 1
                            """,
                            feature=feature, policy=policy
                        )
            
            # Product-Product relationships (if text mentions dependency/compatibility)
            if any(keyword in text for keyword in ["依存", "連携", "統合", "互換", "利用"]):
                product_list = list(products)
                for i in range(len(product_list)):
                    for j in range(i+1, len(product_list)):
                        session.run(
                            """
                            MATCH (p1:Product {name: $p1}), (p2:Product {name: $p2})
                            MERGE (p1)-[r:RELATES_TO]->(p2)
                            SET r.w_struct = 1.0, r.w_attn = 0.0, r.ts = timestamp()
                            SET p1.degree = p1.degree + 1, p2.degree = p2.degree + 1
                            """,
                            p1=product_list[i], p2=product_list[j]
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
    max_nodes: int = None,
    collection_name: str = "lightrag_docs"
) -> Dict:
    """
    Build local subgraph from seed nodes (LightRAG's graph-level retrieval).
    Returns nodes with their beta scores (graph-level scores).
    
    Args:
        seed_nodes: Starting nodes for graph traversal
        max_depth: Maximum depth of traversal
        theta: Minimum score threshold for including nodes
        max_nodes: Maximum number of nodes to visit (for lightweight constraint)
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
        # Check if we've reached the node limit (LightRAG's lightweight constraint)
        if max_nodes and len(visited) >= max_nodes:
            break
        
        new_frontier = []
        
        with neo4j_driver.session() as session:
            for node_name in frontier:
                # Check node limit before processing each frontier node
                if max_nodes and len(visited) >= max_nodes:
                    break
                
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
                    # Check node limit before adding each neighbor
                    if max_nodes and len(visited) >= max_nodes:
                        break
                    
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
            
            # Extract entities from retrieved text using improved extraction function
            entities = extract_entities(text)
            entities_found = entities["products"] + entities["features"] + entities["policies"]
            
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
            # Final fallback: get top nodes from Neo4j based on centrality/degree
            # For global questions, get more nodes
            with neo4j_driver.session() as session:
                # Check if this is a global question
                is_global = any(keyword in question.lower() for keyword in ["すべて", "全て", "all", "すべての", "全ての", "要約", "関係", "すべての製品", "すべての機能"])
                
                if is_global:
                    # For global questions, limit seed_nodes to top_k * 2 to maintain LightRAG's lightweight nature
                    # This ensures that even global questions don't explore too many nodes
                    limit_seed = top_k * 2
                    result = session.run("""
                        MATCH (n)
                        WHERE n.degree IS NOT NULL
                        RETURN n.name as name, n.degree as degree
                        ORDER BY n.degree DESC
                        LIMIT $limit
                    """, limit=limit_seed)
                    for record in result:
                        node_name = record["name"]
                        degree = record.get("degree", 1)
                        seed_nodes.append(node_name)
                        alpha_scores[node_name] = min(degree / 10.0, 1.0)  # Normalize degree to alpha score
                else:
                    # For specific questions, try to extract entities from question itself
                    question_entities = extract_entities(question)
                    extracted = question_entities["products"] + question_entities["features"] + question_entities["policies"]
                    
                    # Also search for partial matches in Neo4j (e.g., "Acme" -> "Acme Search")
                    if not extracted or len(extracted) < top_k:
                        # Extract potential product name keywords from question
                        import re
                        question_words = re.findall(r'\b([A-Z][a-z]+)\b', question)
                        for word in question_words:
                            if word.lower() not in ["the", "and", "or", "not", "is", "are", "was", "were", "will", "can", "does", "do", "did"]:
                                result = session.run("""
                                    MATCH (n)
                                    WHERE n.name CONTAINS $keyword
                                    RETURN n.name as name
                                    LIMIT 5
                                """, keyword=word)
                                for record in result:
                                    node_name = record["name"]
                                    if node_name not in extracted:
                                        extracted.append(node_name)
                                        alpha_scores[node_name] = 0.75  # High score for partial match
                    
                    if extracted:
                        seed_nodes = extracted[:top_k * 2]
                        for node_name in seed_nodes:
                            if node_name not in alpha_scores:
                                alpha_scores[node_name] = 0.8  # Higher score for explicitly mentioned entities
                    else:
                        # Last resort: get random sample of nodes
                        result = session.run("MATCH (n) RETURN n.name as name LIMIT 10")
                        seed_nodes = [r["name"] for r in result]
                        for node_name in seed_nodes:
                            alpha_scores[node_name] = 0.5  # Default alpha for fallback nodes
    
    # Step 2: Graph-level retrieval (high-level) - build local subgraph and get beta scores
    # Limit total visited nodes to top_k * 3 to maintain LightRAG's lightweight nature
    # This ensures that even with many seed_nodes, we don't explore too many nodes
    max_nodes_limit = top_k * 3
    
    try:
        subgraph = build_local_graph(seed_nodes, max_depth=depth, theta=theta, max_nodes=max_nodes_limit)
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
    
    # Heuristic adjustment: ensure explicitly mentioned entities and their features are considered
    question_entities = extract_entities(question)
    explicit_products = question_entities.get("products", [])
    explicit_features = question_entities.get("features", [])

    product_aliases = {"Acme": "Acme Search", "Globex": "Globex Graph"}

    heuristic_products = set(explicit_products)
    heuristic_features = set(explicit_features)

    for alias, canonical in product_aliases.items():
        if alias in question:
            heuristic_products.add(canonical)

    if (heuristic_products or heuristic_features) and neo4j_driver:
        with neo4j_driver.session() as session:
            # Boost explicitly mentioned features
            for feature in heuristic_features:
                all_node_names.add(feature)
                final_scores[feature] = max(final_scores.get(feature, 0.0), 1.0)

            # Boost products and pull their features into the candidate set
            for product in heuristic_products:
                all_node_names.add(product)
                final_scores[product] = max(final_scores.get(product, 0.0), 0.95)

                result = session.run(
                    """
                    MATCH (p:Product {name: $product})-[:HAS_FEATURE]->(f:Feature)
                    RETURN f.name as feature
                    """,
                    product=product,
                )
                for record in result:
                    feature_name = record.get("feature")
                    if feature_name:
                        all_node_names.add(feature_name)
                        final_scores[feature_name] = max(final_scores.get(feature_name, 0.0), 0.9)

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
            result = session.run(
                """
                UNWIND range(0, size($names) - 1) AS idx
                WITH idx, $names[idx] AS target
                MATCH (n {name: target})
                OPTIONAL MATCH (n)-[r]-(related)
                RETURN
                    n.name as name,
                    labels(n)[0] as type,
                    collect(DISTINCT related.name) as related,
                    idx
                ORDER BY idx
                """,
                names=node_names,
            )
            
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

            nodes = []
            seen_nodes = set()
            for node in nodes_info:
                name = node["name"]
                node_type = node["type"]
                if name not in seen_nodes:
                    nodes.append({"name": name, "type": node_type})
                    seen_nodes.add(name)

                if node_type == "Product":
                    feature_result = session.run(
                        """
                        MATCH (:Product {name: $product})-[:HAS_FEATURE]->(f:Feature)
                        RETURN f.name as feature
                        """,
                        product=name,
                    )
                    for feature_record in feature_result:
                        feature_name = feature_record.get("feature")
                        if feature_name and feature_name not in seen_nodes:
                            nodes.append({"name": feature_name, "type": "Feature"})
                            seen_nodes.add(feature_name)
    
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

