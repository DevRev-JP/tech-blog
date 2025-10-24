from fastapi import FastAPI
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
import json
import os

app = FastAPI()

NEO4J_URI="bolt://neo4j:7687"; NEO4J_USER="neo4j"; NEO4J_PASS="password"
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

qdrant = QdrantClient(host="qdrant", port=6333)
COL="docs"
embed = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# 現在のデータセット情報
current_dataset = {"file": "docs.jsonl", "count": 5}

def kg_answer(q: str):
    with driver.session() as s:
        if "何個" in q:
            cy = """MATCH (:Product {name:'Acme Search'})-[:HAS_FEATURE]->(f:Feature)
                    RETURN count(f) AS cnt"""
            res = s.run(cy).data()
            return {"type":"count", "rows": res if res else [{"cnt":0}]}
        if "共通" in q:
            cy = """MATCH (p1:Product {name:'Acme Search'})-[:HAS_FEATURE]->(f:Feature)
                    MATCH (p2:Product {name:'Globex Graph'})-[:HAS_FEATURE]->(f)
                    RETURN collect(DISTINCT f.name) AS common"""
            res = s.run(cy).data()
            return {"type":"intersection", "rows": res if res else [{"common":[]}]}
        if "Semantic Index を提供する製品で" in q:
            # Q2-差分: Semantic Index を提供するが Policy Audit を提供していない製品
            cy = """MATCH (p:Product)-[:HAS_FEATURE]->(f1:Feature {name:'Semantic Index'})
                    WHERE NOT EXISTS { (p)-[:HAS_FEATURE]->(:Feature {name:'Policy Audit'}) }
                    RETURN collect(DISTINCT p.name) AS products"""
            res = s.run(cy).data()
            return {"type":"diff", "rows": res if res else [{"products":[]}]}
        if "違い" in q or ("Acme Search" in q and "Globex Graph" in q):
            cy = """MATCH (p1:Product {name:'Acme Search'})-[:HAS_FEATURE]->(f:Feature)
                    WITH collect(DISTINCT f.name) AS features_a
                    MATCH (p2:Product {name:'Globex Graph'})-[:HAS_FEATURE]->(f2:Feature)
                    WITH features_a, collect(DISTINCT f2.name) AS features_b
                    RETURN
                      [x IN features_a WHERE NOT x IN features_b] AS only_in_a,
                      [x IN features_b WHERE NOT x IN features_a] AS only_in_b"""
            res = s.run(cy).data()
            return {"type":"diff", "rows": res if res else [{"only_in_a":[],"only_in_b":[]}]}
        if "機能" in q and "Acme" in q:
            cy = """MATCH (:Company {name:'Acme'})-[:BUILDS]->(p:Product)-[:HAS_FEATURE]->(f:Feature)
                    RETURN p.name AS product, collect(DISTINCT f.name) AS features"""
            res = s.run(cy).data()
            return {"type":"set", "rows": res if res else [{"features":[]}]}
        if "どのポリシー" in q or "規制" in q:
            cy = """MATCH (pol:Policy)-[:REGULATES]->(:Product {name:'Globex Graph'})
                    RETURN collect(pol.id) AS policies"""
            res = s.run(cy).data()
            return {"type":"policies", "rows": res if res else [{"policies":[]}]}
        if "持たない" in q:
            cy = """MATCH (f:Feature) WHERE f.name <> 'Semantic Index'
                    RETURN collect(DISTINCT f.name) AS features"""
            res = s.run(cy).data()
            return {"type":"negation", "rows": res if res else [{"features":[]}]}
    return {"type":"unknown","rows":[]}

def rag_answer(q: str, k=3):
    v = embed.encode([q])[0].tolist()
    hits = qdrant.search(collection_name=COL, query_vector=v, limit=k)
    texts = [h.payload["text"] for h in hits]
    if "何個" in q:
        n = 0
        if any("Realtime" in t for t in texts): n+=1
        if any("Semantic Index" in t for t in texts): n+=1
        if any("Policy Audit" in t for t in texts): n+=1
        return {"cnt": n}
    if "共通" in q:
        common = []
        if any("Acme" in t and "Realtime" in t for t in texts) and any("Globex" in t and "Realtime" in t for t in texts):
            common.append("Realtime Query")
        if any("Acme" in t and "Semantic Index" in t for t in texts) and any("Globex" in t and "Semantic Index" in t for t in texts):
            common.append("Semantic Index")
        return {"common": sorted(set(common))}
    if "Semantic Index を提供する製品で" in q:
        # Q2-差分: Semantic Index を提供するが Policy Audit を提供していない製品
        products = []
        if any("Acme" in t and "Semantic Index" in t for t in texts) and not any("Acme" in t and "Policy Audit" in t for t in texts):
            products.append("Acme Search")
        if any("Globex" in t and "Semantic Index" in t for t in texts) and not any("Globex" in t and "Policy Audit" in t for t in texts):
            products.append("Globex Graph")
        return {"products": sorted(set(products))}
    if "違い" in q or ("Acme Search" in q and "Globex Graph" in q):
        only_a = "Realtime Query" if any("Realtime" in t for t in texts) else ""
        only_b = "Policy Audit" if any("Policy Audit" in t for t in texts) else ""
        return {"only_in_a":[x for x in [only_a] if x], "only_in_b":[x for x in [only_b] if x]}
    if "機能" in q and "Acme" in q:
        feats = []
        if any("Realtime" in t for t in texts): feats.append("Realtime Query")
        if any("Semantic Index" in t for t in texts): feats.append("Semantic Index")
        return {"features": sorted(set(feats))}
    if "どのポリシー" in q or "規制" in q:
        return {"policies": ["POL-002"] if any("POL-002" in t for t in texts) else []}
    if "持たない" in q:
        feats = []
        if any("Policy Audit" in t for t in texts): feats.append("Policy Audit")
        if any("Realtime" in t for t in texts): feats.append("Realtime Query")
        if any("Semantic Index" in t for t in texts): feats.append("Semantic Index")
        return {"features": sorted(set(feats))}
    return {"texts": texts}

@app.get("/ask/kg")
def ask_kg(q: str): return kg_answer(q)

@app.get("/ask/rag")
def ask_rag(q: str): return rag_answer(q)

@app.get("/eval")
def eval_all():
    # 毎回 questions.json を読み込む（動的変更に対応）
    with open("questions.json") as f:
        qs = json.load(f)
    res=[]; ok_rag=ok_kg=0
    by_category={"simple":{"kg":0,"rag":0,"total":0},"scale_dependent":{"kg":0,"rag":0,"total":0},"scale_stable":{"kg":0,"rag":0,"total":0},"kg_exclusive":{"kg":0,"rag":0,"total":0}}

    for it in qs:
        q=it["ask"]; kg=kg_answer(q); rag=rag_answer(q)
        vr=False; vk=False; kg_result=kg["rows"][0] if kg["rows"] else {}
        cat=it.get("category","unknown")

        if it["id"]=="Q1-集合":
            exp=set(it["expected"])
            vr=(set(rag.get("features",[]))==exp)
            vk=(set(kg_result.get("features",[]))==exp)
        elif it["id"]=="Q2-差分":
            exp=set(it["expected"])
            vr=(set(rag.get("products",[]))==exp)
            vk=(set(kg_result.get("products",[]))==exp)
        elif it["id"]=="Q3-経路":
            exp=set(it["expected"])
            vr=(set(rag.get("policies",[]))==exp)
            vk=(set(kg_result.get("policies",[]))==exp)
        elif it["id"]=="Q4-否定":
            exp=set(it["expected"])
            vr=(set(rag.get("features",[]))==exp)
            vk=(set(kg_result.get("features",[]))==exp)
        elif it["id"]=="Q5-交差":
            exp=set(it["expected"])
            vr=(set(rag.get("common",[]))==exp)
            vk=(set(kg_result.get("common",[]))==exp)

        ok_rag += int(vr); ok_kg += int(vk)
        if cat in by_category:
            by_category[cat]["total"]+=1
            by_category[cat]["kg"]+=int(vk)
            by_category[cat]["rag"]+=int(vr)
        res.append({"id":it["id"],"category":cat,"rag_ok":vr,"kg_ok":vk,"scale_note":it.get("scale_note","")})

    return {
        "summary":{"kg_correct":ok_kg,"kg_total":len(qs),"rag_correct":ok_rag,"rag_total":len(qs)},
        "by_category":{k:{"kg":v["kg"],"rag":v["rag"],"total":v["total"]} for k,v in by_category.items() if v["total"]>0},
        "cases":res,
        "dataset":current_dataset
    }

@app.post("/switch-dataset")
def switch_dataset(file: str):
    """データセットを動的に切り替える

    使い方:
    - curl -X POST "http://localhost:8000/switch-dataset?file=docs.jsonl"
    - curl -X POST "http://localhost:8000/switch-dataset?file=docs-50.jsonl"
    """
    global current_dataset

    if file not in ["docs.jsonl", "docs-50.jsonl"]:
        return {"error": f"Unknown dataset: {file}", "available": ["docs.jsonl", "docs-50.jsonl"]}

    try:
        # ファイルを読み込む
        with open(file) as f:
            texts = [json.loads(l) for l in f]

        # ベクトル埋め込みを計算
        vecs = embed.encode([t["text"] for t in texts])

        # Qdrant を初期化（既存データを削除）
        try:
            qdrant.delete_collection(collection_name=COL)
        except:
            pass

        qdrant.recreate_collection(
            collection_name=COL,
            vectors_config=VectorParams(size=len(vecs[0]), distance=Distance.COSINE)
        )

        # ドキュメントをアップサート
        points = [PointStruct(id=i+1, vector=vecs[i], payload=texts[i]) for i in range(len(texts))]
        qdrant.upsert(collection_name=COL, points=points)

        # グローバル変数を更新
        current_dataset = {"file": file, "count": len(texts)}

        return {
            "status": "success",
            "dataset": current_dataset,
            "message": f"Switched to {file} ({len(texts)} documents)"
        }
    except FileNotFoundError:
        return {"error": f"File not found: {file}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/dataset")
def get_dataset():
    """現在のデータセット情報を取得"""
    return current_dataset

@app.get("/questions")
def get_questions():
    """現在の評価用質問セットを取得"""
    with open("questions.json") as f:
        return json.load(f)

@app.post("/update-question")
def update_question(question_id: str, new_question: str):
    """特定の質問を更新（コンテナ再起動なしで動的変更可能）

    使い方:
    - curl -X POST "http://localhost:8000/update-question?question_id=Q2-差分&new_question=新しい質問文"
    """
    try:
        with open("questions.json") as f:
            questions = json.load(f)

        # 該当する質問を検索して更新
        for q in questions:
            if q["id"] == question_id:
                q["ask"] = new_question
                # ファイルに保存
                with open("questions.json", "w") as f:
                    json.dump(questions, f, indent=2, ensure_ascii=False)
                return {
                    "status": "success",
                    "message": f"Updated {question_id}",
                    "question": q
                }

        return {"error": f"Question {question_id} not found"}
    except Exception as e:
        return {"error": str(e)}