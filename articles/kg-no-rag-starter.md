---
title: "RAGなしで始めるナレッジグラフQA——コンテナで再現する比較検証"
emoji: "🧠"
type: "tech"
topics: ["ナレッジグラフ", "Neo4j", "Cypher", "SPARQL", "SHACL"]
published: false
---

# RAG なしで始めるナレッジグラフ QA——コンテナで再現する比較検証

**ねらい**
RAG（ベクタ検索）を使わず、**ナレッジグラフだけで論理的に答える**最小構成を、Docker だけで動かして確認する。差分・否定・経路・カウントなど、**RAG が失敗しやすい問い**で、**KG（Cypher/SPARQL）が正確**に答えられることを手元で再現する。

---

## 重要な注釈：RAG と KG は対立ではなく補完関係

本記事のタイトルは「RAG なし」ですが、これは「RAG を否定する」という意味ではありません。むしろ、**KG と RAG の役割分担を理解するための比較実験** です。

実務では、KG と RAG は併用されます：

- **RAG の役割**：大量の非構造化テキスト（ドキュメント、記事、ログ）から関連情報を素早く検索し、文脈を提供する
- **KG の役割**：構造化された知識（エンティティ・関係・ルール）から論理的に推論し、正確な回答を導く

本記事では、**KG が得意とする領域を明確にするために、敢えて KG 単独での動作を検証** しています。実装では RAG（Qdrant）も起動していますが、意図的に失敗するシナリオを設定し、KG の価値を浮き彫りにしています。

現実のシステムでは、「ユーザーの問いが KG で答えられるか、RAG で探索すべきか」を自動判定し、適切に組み合わせることが重要です。

---

## 1. 何を用意するか（ローカルのみ）

- macOS（または Linux/WSL2）
- **Docker / Docker Compose v2**
- `curl`（動作確認）
- 使うもの：
  - **Neo4j 5**（Property Graph, Cypher）
  - **Qdrant**（RAG ベースライン用のベクタ DB：比較対象。RAG 自体は“失敗例”として参照）

> この記事は **RAG を“使わない”実装が主役**ですが、比較のため最小の RAG ベースラインも同時起動します。

---

## 2. 試験用の小さな“真実”ドメイン

- ノード：`Company`、`Product`、`Feature`、`Policy`
- 関係：`BUILDS`、`HAS_FEATURE`、`REGULATES`、`DEPENDS_ON`
- 意味問合せの型：**集合**（一覧）、**対比**（差分）、**経路**（到達/依存）、**否定**（除外）、**カウント**（個数）

---

## 3. 叩けば動く構成（docker-compose + 初期データ）

プロジェクト任意ディレクトリで以下を作成します。

**`docker-compose.yml`**

```yaml
version: "3.9"
services:
  neo4j:
    image: neo4j:5
    container_name: neo4j-kgnr
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant-rag
    ports: ["6333:6333"]
    volumes:
      - qdrant_storage:/qdrant/storage

  api:
    image: python:3.11-slim
    container_name: api-compare
    depends_on:
      neo4j:
        condition: service_started
      qdrant:
        condition: service_started
    working_dir: /app
    ports: ["8000:8000"]
    volumes: ["./app:/app"]
    environment:
      DOCS_FILE: ${DOCS_FILE:-docs.jsonl}
    command: >
      sh -c "pip install -q fastapi uvicorn[standard] neo4j qdrant-client sentence-transformers huggingface-hub==0.17.3
      && python seed.py && uvicorn main:app --host 0.0.0.0 --port 8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  neo4j_data:
  qdrant_storage:
```


続いて、`app/` ディレクトリを作り、初期データと API スクリプトを配置します。

---

## 4. 実行と動作確認

### 小規模版（5項目）で基本動作を確認

```bash
docker compose down -v
docker compose up --detach
sleep 45

# 評価実行
curl -s http://localhost:8000/eval | jq '.'
```

**期待される結果（KG: 5/5, RAG: 2/5）**

```json
{
  "summary": {
    "kg_correct": 5,
    "kg_total": 5,
    "rag_correct": 2,
    "rag_total": 5
  },
  "cases": [
    { "id": "Q1-集合", "rag_ok": true, "kg_ok": true },
    { "id": "Q2-差分", "rag_ok": false, "kg_ok": true },
    { "id": "Q3-経路", "rag_ok": false, "kg_ok": true },
    { "id": "Q4-否定", "rag_ok": false, "kg_ok": true },
    { "id": "Q5-交差", "rag_ok": true, "kg_ok": true }
  ]
}
```

### 大規模版（50項目）でスケール依存性を実証

```bash
docker compose down -v
export DOCS_FILE=docs-50.jsonl
docker compose up --detach
sleep 45

curl -s http://localhost:8000/eval | jq '.'
```

**期待される結果（KG: 5/5, RAG: 0/5）**

```json
{
  "summary": {
    "kg_correct": 5,
    "kg_total": 5,
    "rag_correct": 0,
    "rag_total": 5
  },
  "cases": [
    { "id": "Q1-集合", "rag_ok": false, "kg_ok": true },
    { "id": "Q2-差分", "rag_ok": false, "kg_ok": true },
    { "id": "Q3-経路", "rag_ok": false, "kg_ok": true },
    { "id": "Q4-否定", "rag_ok": false, "kg_ok": true },
    { "id": "Q5-交差", "rag_ok": false, "kg_ok": true }
  ]
}
```

---

## 5. 結果の解釈

### なぜこの差が出たのか

| 質問型 | KG | RAG(5項目) | RAG(50項目) | 理由 |
|------|----|----|----|----|
| **Q1-集合** | ✅ | ✅ | ❌ | 集合操作は明確だが、ノイズが多いと埋もれる |
| **Q2-差分** | ✅ | ❌ | ❌ | 差分操作はベクトル検索に不向き |
| **Q3-経路** | ✅ | ❌ | ❌ | グラフの多段階経路をベクトル検索では追跡不可 |
| **Q4-否定** | ✅ | ❌ | ❌ | 論理的否定条件が曖昧なテキストでは実現困難 |
| **Q5-交差** | ✅ | ✅ | ❌ | 共通要素は明確だが、スケールで失敗 |

### KG の強み

1. **スケール不変性** — データが 5 件でも 50 件でも、Cypher クエリの結果は同じ
2. **論理厳密性** — 集合、差分、否定、経路追跡を正確に実行
3. **構造理解** — ドメイン知識をグラフ構造として記述すれば、複雑な関係も明確に表現可能

### RAG の限界

1. **スケール依存性** — データが増えるとベクトル検索のノイズが増加
2. **操作的な問い** — 差分、否定、カウント、経路追跡は得意でない
3. **曖昧性** — テキストが増えるほど意図を正確に拾いづらくなる

---

## 6. さらに学ぶために

### 理論的背景

本記事で実装した内容の理論的背景やアーキテクチャ的な位置づけについては、以下の記事をご覧ください：

- **「RAGを超える知識統合──ナレッジグラフで"つながる推論"を実現する」**
  - RAG と KG の本質的な違い
  - GraphRAG と KG の関係性
  - エンタープライズ知識グラフの戦略的な役割

### 技術資料

- **Neo4j ドキュメント**: https://neo4j.com/docs/
- **Cypher 解説**: https://neo4j.com/docs/cypher-manual/
- **セマンティック Web との統合**: SPARQL、RDF、OWL
- **スケールアップ**: Wikidata、DBpedia への連携

---

※本記事は AI を活用して執筆しています。
