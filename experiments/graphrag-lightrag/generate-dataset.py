#!/usr/bin/env python3
"""
Generate large-scale datasets for GraphRAG/LightRAG experiments.
This script generates datasets with varying numbers of nodes (300, 500, 1000)
with high connectivity (average degree 3-5).
"""
import json
import random
import argparse
from typing import Set

# Product name templates
PRODUCT_PREFIXES = [
    "CloudBridge", "DataVault", "NetworkGuard", "AutoScale", "Integration", "MonitorFlow",
    "AnalyticsCore", "Workflow", "Cache", "MessageQueue", "StorageSync", "Authentication",
    "LogAggregator", "Deployment", "Configuration", "Document", "Report", "Backup",
    "Performance", "Code", "Test", "VirtualMachine", "LoadBalancer", "Database",
    "Service", "EventStream", "Metrics", "Notification", "Form", "DataQuality",
    "Scheduler", "Visualization", "Search", "Compliance", "Risk", "Incident",
    "Capacity", "Cost", "Security", "API", "Content", "User", "Email", "Chat"
]

PRODUCT_SUFFIXES = [
    "Platform", "Pro", "Suite", "Manager", "Engine", "System", "Tool", "Service",
    "Core", "Hub", "Framework", "Studio", "Builder", "Search", "Graph", "Index",
    "Vault", "Guard", "Bridge", "Optimizer", "Collector", "Analyzer", "Scanner",
    "Delivery", "Campaign", "Bot"
]

FEATURE_NAMES = [
    "Semantic Index", "Policy Audit", "Realtime Query", "Data Encryption",
    "Access Control", "Audit Logging", "Performance Monitoring", "Auto Scaling",
    "Load Balancing", "Backup Restore", "Disaster Recovery", "Multi Region",
    "API Gateway", "Rate Limiting", "Caching Layer", "Search Index",
    "Analytics Dashboard", "Alert System", "Workflow Engine", "Task Scheduler"
]

FEATURE_ADJECTIVES = [
    "Advanced", "Adaptive", "Augmented", "Autonomous", "Cognitive", "Collaborative",
    "Continuous", "Distributed", "Dynamic", "Enterprise", "Hybrid", "Intelligent",
    "Predictive", "Realtime", "Secure", "Self-Healing", "Smart", "Streamlined", "Unified", "Virtual"
]

FEATURE_SUFFIXES = [
    "Adapter", "Agent", "Analyzer", "Assistant", "Bridge", "Builder", "Console",
    "Engine", "Extension", "Framework", "Gateway", "Hub", "Layer", "Module",
    "Optimizer", "Orchestrator", "Pipeline", "Service", "Suite", "Toolkit"
]

POLICY_TEMPLATES = [
    ("Personal Data Protection", "POL"),
    ("AI Model Governance", "POL"),
    ("Security Compliance", "POL"),
    ("Data Retention", "POL"),
    ("Access Control", "POL"),
    ("Audit Requirements", "POL"),
    ("Privacy Regulation", "POL"),
    ("GDPR Compliance", "POL")
]


def generate_product_name():
    """Generate a random product name."""
    prefix = random.choice(PRODUCT_PREFIXES)
    suffix = random.choice(PRODUCT_SUFFIXES)
    # Avoid duplicate combinations
    return f"{prefix} {suffix}"


def generate_relationship_text(product, features, policies, other_products):
    """Generate natural language text describing relationships."""
    texts = []
    
    # Product description
    feature_list = ", ".join(features[:3])
    if len(features) > 3:
        feature_list += f", {features[3]}など"
    
    product_text = f"{product} は企業向けソリューションです。{feature_list} 機能を提供しています。"
    texts.append(product_text)
    
    # Feature descriptions
    for feature in features[:2]:
        feature_text = f"{feature} 機能は、{product} の主要機能の一つです。"
        texts.append(feature_text)
    
    # Policy relationships
    if policies:
        policy_list = ", ".join([f"{name}（{pid}）" for name, pid in policies[:2]])
        policy_text = f"{policy_list} は {product} に関連するポリシーです。コンプライアンス要件を満たす必要があります。"
        texts.append(policy_text)
    
    # Product-Product relationships (for connectivity)
    if other_products:
        related_product = random.choice(other_products)
        relation_keywords = ["依存", "連携", "統合", "互換"]
        keyword = random.choice(relation_keywords)
        relation_text = f"{product} は {related_product} と{keyword}関係があります。相互運用性が高いです。"
        texts.append(relation_text)
    
    return " ".join(texts)


def build_feature_list(target_count, known_features):
    """Generate a sufficiently large pool of unique feature names."""
    features = []
    seen = set()
    
    def add_feature(name):
        normalized = name.replace("-", " ").strip()
        name_to_store = normalized if normalized else name
        if name_to_store and name_to_store not in seen:
            features.append(name_to_store)
            seen.add(name_to_store)
    
    # Ensure known features appear first
    for feat in known_features:
        add_feature(feat)
    
    # Add base names
    for feat in FEATURE_NAMES:
        add_feature(feat)
        if len(features) >= target_count:
            return features[:target_count]
    
    # Generate adjective + base combinations
    adjective_combos = [f"{adj} {base}" for adj in FEATURE_ADJECTIVES for base in FEATURE_NAMES]
    random.shuffle(adjective_combos)
    for candidate in adjective_combos:
        add_feature(candidate)
        if len(features) >= target_count:
            return features[:target_count]
    
    # Generate base + suffix combinations
    suffix_combos = [f"{base} {suffix}" for base in FEATURE_NAMES for suffix in FEATURE_SUFFIXES]
    random.shuffle(suffix_combos)
    for candidate in suffix_combos:
        add_feature(candidate)
        if len(features) >= target_count:
            return features[:target_count]
    
    # Fallback: create numbered synthetic features
    counter = 1
    while len(features) < target_count:
        add_feature(f"Synthetic Feature {counter}")
        counter += 1
    
    return features[:target_count]


def generate_dataset(target_nodes, avg_degree=4):
    """
    Generate a dataset with approximately target_nodes nodes.
    
    Strategy:
    - Generate products (60% of nodes)
    - Generate features (25% of nodes)
    - Generate policies (15% of nodes)
    - Create relationships to achieve avg_degree average connectivity
    """
    import sys
    random.seed(42)  # Reproducibility
    
    print(f"📊 データセット生成開始: 目標ノード数={target_nodes}, 平均次数={avg_degree}")
    
    # Calculate node counts
    n_products = int(target_nodes * 0.6)
    n_features = int(target_nodes * 0.25)
    n_policies = int(target_nodes * 0.15)
    
    print(f"  ノード構成: 製品={n_products}, 機能={n_features}, ポリシー={n_policies}")
    print()
    
    # Generate unique products
    # Always include known entities from test questions for compatibility
    print("🔄 製品ノード生成中...", end="", flush=True)
    known_products = ["Acme Search", "Globex Graph"]
    products = known_products.copy()
    seen_products = set(known_products)
    
    while len(products) < n_products:
        product = generate_product_name()
        if product not in seen_products:
            products.append(product)
            seen_products.add(product)
            # Progress update every 10 products
            if len(products) % 10 == 0 or len(products) == n_products:
                progress = (len(products) / n_products) * 100
                print(f"\r🔄 製品ノード生成中... {len(products)}/{n_products} ({progress:.1f}%)", end="", flush=True)
    print(f"\r✓ 製品ノード生成完了: {len(products)}/{n_products} (100.0%)")
    
    # Use a subset of features, ensure some are shared
    # Always include known features from test questions for compatibility
    known_features = ["Semantic Index", "Policy Audit", "Realtime Query"]
    print("🔄 機能ノード生成中...", end="", flush=True)
    features = build_feature_list(n_features, known_features)
    print(f"\r✓ 機能ノード生成完了: {len(features)}/{n_features} (100.0%)")
    
    # Generate policies
    # Always include known policies from test questions for compatibility
    print("🔄 ポリシーノード生成中...", end="", flush=True)
    known_policies = [
        ("Personal Data Protection", "POL-001"),
        ("AI Model Governance", "POL-002")
    ]
    policies = known_policies.copy()
    
    # Add more policies if needed
    for i in range(len(known_policies), n_policies):
        policy_name, prefix = random.choice(POLICY_TEMPLATES)
        policy_id = f"{prefix}-{str(i+1).zfill(3)}"
        # Avoid duplicates
        if not any(p[1] == policy_id for p in policies):
            policies.append((policy_name, policy_id))
        # Progress update
        if len(policies) % 5 == 0 or len(policies) >= n_policies:
            progress = (len(policies) / n_policies) * 100
            print(f"\r🔄 ポリシーノード生成中... {len(policies)}/{n_policies} ({progress:.1f}%)", end="", flush=True)
    print(f"\r✓ ポリシーノード生成完了: {len(policies)}/{n_policies} (100.0%)")
    print()
    
    # Calculate total edges needed for avg_degree
    total_nodes = n_products + n_features + n_policies
    total_edges_needed = int((total_nodes * avg_degree) / 2)  # Undirected, so divide by 2
    
    # Create documents with relationships
    print("🔄 関係とドキュメント生成中...")
    docs = []
    doc_id = 1
    
    # Assign features to products (Product-Feature edges)
    # Each product gets 2-5 features
    # Ensure known products have known features for test compatibility
    product_feature_map = {}
    
    # Special assignment for known products to match test questions
    if "Acme Search" in products:
        product_feature_map["Acme Search"] = ["Semantic Index", "Realtime Query"]
    if "Globex Graph" in products:
        product_feature_map["Globex Graph"] = ["Semantic Index", "Policy Audit"]
    
    # Assign features to other products
    for product in products:
        if product not in product_feature_map:  # Skip if already assigned
            n_product_features = random.randint(2, 5)
            product_features = random.sample(features, min(n_product_features, len(features)))
            product_feature_map[product] = product_features
    
    # Assign policies to products/features (Policy edges)
    policy_assignments = {}
    policy_population = products + features
    for policy_name, policy_id in policies:
        targets: Set[str] = set()
        if policy_population:
            sample_upper = min(len(policy_population), max(3, random.randint(3, 10)))
            targets.update(random.sample(policy_population, sample_upper))
        
        # Ensure known policies are assigned to known products for test compatibility
        if policy_id == "POL-001" and "Acme Search" in products:
            targets.add("Acme Search")
        if policy_id == "POL-002":
            if "Acme Search" in products:
                targets.add("Acme Search")
            if "Globex Graph" in products:
                targets.add("Globex Graph")
        
        policy_assignments[policy_id] = {
            "name": policy_name,
            "targets": targets
        }
    
    # Create product documents
    print("  📝 製品ドキュメント生成中...", end="", flush=True)
    for i, product in enumerate(products):
        product_features = product_feature_map[product]
        
        # Find related products (for Product-Product edges)
        related_products = []
        if i > 0 and random.random() < 0.4:  # 40% chance of having a relation
            related_products = random.sample(products[:i], min(1, len(products[:i])))
        
        # Find applicable policies
        applicable_policies = []
        for policy_id, info in policy_assignments.items():
            targets = info["targets"]
            if product in targets or any(f in targets for f in product_features):
                applicable_policies.append((info["name"], policy_id))
        
        text = generate_relationship_text(product, product_features, applicable_policies[:2], related_products)
        docs.append({"id": f"d{doc_id}", "text": text})
        doc_id += 1
        
        # Progress update every 20 products
        if (i + 1) % 20 == 0 or (i + 1) == len(products):
            progress = ((i + 1) / len(products)) * 100
            print(f"\r  📝 製品ドキュメント生成中... {i+1}/{len(products)} ({progress:.1f}%)", end="", flush=True)
    print()
    
    # Create feature documents
    print("  📝 機能ドキュメント生成中...", end="", flush=True)
    feature_docs_count = 0
    for feature in features[:min(len(features), n_features)]:
        # Feature can be related to multiple products
        related_products = [p for p, feats in product_feature_map.items() if feature in feats]
        if related_products:
            related_products_sample = random.sample(related_products, min(3, len(related_products)))
            text = f"{feature} 機能は、{', '.join(related_products_sample[:2])} など複数の製品で利用されています。"
            docs.append({"id": f"d{doc_id}", "text": text})
            doc_id += 1
            feature_docs_count += 1
            # Progress update
            if feature_docs_count % 5 == 0:
                total_features = min(len(features), n_features)
                progress = (feature_docs_count / total_features) * 100 if total_features > 0 else 100
                print(f"\r  📝 機能ドキュメント生成中... {feature_docs_count}/{total_features} ({progress:.1f}%)", end="", flush=True)
    # Final progress
    total_features = min(len(features), n_features)
    if feature_docs_count > 0:
        print(f"\r  📝 機能ドキュメント生成中... {feature_docs_count}/{total_features} (100.0%)", end="", flush=True)
    print()
    
    # Create policy documents
    print("  📝 ポリシードキュメント生成中...", end="", flush=True)
    for i, (policy_name, policy_id) in enumerate(policies):
        assignment = policy_assignments.get(policy_id)
        targets = list(assignment["targets"]) if assignment else []
        if targets:
            sample_count = min(3, len(targets))
            target_sample = random.sample(targets, sample_count)
            joined_targets = ", ".join(target_sample[:2])
            text = f"{assignment['name']}（{policy_id}）は {joined_targets} に関連するポリシーです。規制要件を満たす必要があります。"
            docs.append({"id": f"d{doc_id}", "text": text})
            doc_id += 1
        # Progress update
        if (i + 1) % 5 == 0 or (i + 1) == len(policies):
            progress = ((i + 1) / len(policies)) * 100
            print(f"\r  📝 ポリシードキュメント生成中... {i+1}/{len(policies)} ({progress:.1f}%)", end="", flush=True)
    print()
    
    # Add some additional relationship documents to increase connectivity
    additional_docs = max(0, int(target_nodes * 0.2))  # 20% more docs for relationships
    print(f"  📝 追加関係ドキュメント生成中... ({additional_docs}件)", end="", flush=True)
    for i in range(additional_docs):
        if random.random() < 0.7:  # 70% product-product relationships
            if len(products) >= 2:
                p1, p2 = random.sample(products, 2)
                relation = random.choice(["依存", "連携", "統合", "互換"])
                text = f"{p1} と {p2} は{relation}関係にあり、相互運用性が高いです。"
                docs.append({"id": f"d{doc_id}", "text": text})
                doc_id += 1
        else:  # Feature-feature or feature-policy relationships
            if features and policies:
                feature = random.choice(features)
                policy_name, policy_id = random.choice(policies)
                text = f"{feature} 機能は {policy_name}（{policy_id}）の要件に対応しています。"
                docs.append({"id": f"d{doc_id}", "text": text})
                doc_id += 1
        
        # Progress update every 10 docs
        if (i + 1) % 10 == 0 or (i + 1) == additional_docs:
            progress = ((i + 1) / additional_docs) * 100 if additional_docs > 0 else 100
            print(f"\r  📝 追加関係ドキュメント生成中... {i+1}/{additional_docs} ({progress:.1f}%)", end="", flush=True)
    print()
    print()
    print(f"✅ ドキュメント生成完了: 合計 {len(docs)} 件")
    
    return docs


def main():
    parser = argparse.ArgumentParser(description="Generate large-scale datasets for experiments")
    parser.add_argument("--size", type=int, required=True, choices=[300, 500, 1000],
                       help="Target number of nodes (300, 500, or 1000)")
    parser.add_argument("--degree", type=int, default=4,
                       help="Target average degree (default: 4)")
    parser.add_argument("--output", type=str, required=True,
                       help="Output JSONL file path")
    
    args = parser.parse_args()
    
    print(f"Generating dataset with ~{args.size} nodes (avg degree: {args.degree})...")
    docs = generate_dataset(args.size, args.degree)
    
    print(f"Generated {len(docs)} documents")
    print(f"Estimated nodes: ~{args.size} (products: {int(args.size*0.6)}, features: {int(args.size*0.25)}, policies: {int(args.size*0.15)})")
    
    # Write to JSONL
    with open(args.output, "w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    
    print(f"✓ Dataset written to {args.output}")


if __name__ == "__main__":
    main()
