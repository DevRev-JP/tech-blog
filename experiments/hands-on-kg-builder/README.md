# hands-on-kg-builder

Zenn本「ナレッジグラフ × LLMで作る次世代RAG」ch5「KGの作り方」のサンプル実装です。
ローカル環境（Docker + Ollama + Neo4j）でKGの構築からLLM連携まで体験できます。

**本（関連chapter）**: [ch5 KGの作り方](https://zenn.dev/knowledge_graph/books/knowledge-graph-llm-guide)

---

## クイックスタート

### Step 1: 環境設定

```bash
cp .env.example .env
# .env を開いて NEO4J_PASSWORD を設定する
```

### Step 2: コンテナ起動

```bash
docker compose up -d
# Ollamaモデルのダウンロード（初回のみ）
docker exec kg-ollama ollama pull llama3.2
```

### Step 3: KG構築とQA実行

```bash
pip install -r requirements.txt
python app/build_kg.py   # CSVからNeo4jへデータ投入
python app/qa.py         # 自然言語でKGに質問
```

---

## 動作確認コマンド

```bash
# Neo4j Browserで確認（ブラウザで開く）
open http://localhost:7474

# Ollama動作確認
curl http://localhost:11434/api/generate \
  -d '{"model":"llama3.2","prompt":"Hello","stream":false}'
```

---

## ディレクトリ構成

```
hands-on-kg-builder/
├── README.md              # このファイル（ch5との対応関係、クイックスタート）
├── docker-compose.yml     # Neo4j + Ollama構成
├── .env.example           # 環境変数サンプル
├── requirements.txt       # Pythonパッケージ一覧
├── data/
│   ├── engineers.csv      # サンプルデータ（エンジニア）
│   └── bugs.csv           # サンプルデータ（バグ）
└── app/
    ├── build_kg.py        # KnowledgeGraphBuilderクラス + main
    └── qa.py              # LangChain QAチェーン
```

---

## ch5との対応関係

| ch5のセクション | 実装ファイル |
|---|---|
| ローカル環境のセットアップ（Docker Compose） | docker-compose.yml |
| データ投入スクリプト（例1） | app/build_kg.py |
| LangChainとNeo4jの連携（例2） | app/qa.py |
| 前提：サンプルCSVの構造 | data/engineers.csv, data/bugs.csv |

---

## 注意事項

**Cypherクエリの精度について**
`qa.py` はローカルLLM（llama3.2）でCypherを自動生成します。3Bパラメータのモデルではクエリの精度に限界があり、フィールド名の誤認やリレーション方向の逆転が起きることがあります。より高精度な結果にはClaudeなどのクラウドLLMの利用を推奨します（`qa.py` 末尾のコメントを参照）。

**メモリ要件**
llama3.2（3Bモデル、2GB）を動かすには、Dockerホストに **4GB以上の空きメモリ** が必要です。
