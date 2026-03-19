# langchain-kg-agent

Zenn本「ナレッジグラフとLLMで作るAIシステム」第8章「AI AgentとKG：L5エージェントを実現する知識基盤」のサンプル実装です。

参照：[第8章 kg-and-ai-agents.md](../../books/knowledge-graph-llm-guide/kg-and-ai-agents.md)

---

## 概要

LangChainとNeo4jを組み合わせ、AI AgentがナレッジグラフをReadし、Reasonし、Writeする3つのパターンを実装します。カスタマーサポートシナリオを題材に、KGが「誰が何を担当しているか」「エスカレーションすべきか」を構造的に判断する仕組みを示します。

---

## アーキテクチャ

### 3つのパターン

| パターン | ファイル | 説明 |
|--------|---------|------|
| **Read** | `app/agent_read.py` | KGから担当チーム・SLA・プランを取得し、LLMが回答を生成する |
| **LangChain Tool** | `app/agent_langchain.py` | KGクエリをLangChainのToolとして定義し、AgentExecutorで自律的に使い回す |
| **エンドツーエンド** | `app/agent_e2e.py` | Read・Reason・Writeを1リクエスト内で統合した完全実装 |

---

## 前提条件

- Docker（Docker Composeが使えること）
- Python 3.11 以上
- Ollama（`llama3.2` モデルのダウンロードが必要）

### Ollamaのモデルダウンロード（初回のみ）

コンテナ起動後に以下を実行してください。数分かかります。

```bash
docker exec kg-ollama ollama pull llama3.2
```

---

## クイックスタート

### 1. 環境変数ファイルの準備

```bash
cp .env.example .env
# .envを開き、NEO4J_PASSWORDに任意の強いパスワードを設定する
```

### 2. Neo4j・Ollamaをコンテナで起動

```bash
docker compose up -d
```

起動確認（Neo4j BrowserはURLで確認できます）：

```
Neo4j Browser: http://localhost:7474
Ollama:        http://localhost:11434
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. サンプルデータ投入

```bash
python app/build_kg.py
```

`data/customers.csv`（10件）と `data/tickets.csv`（15件）がNeo4jに投入されます。

### 5. 各Agentスクリプトの実行

**Readパターン（KGから情報取得）：**

```bash
python app/agent_read.py
```

**LangChain Tool + AgentExecutor：**

```bash
python app/agent_langchain.py
```

**エンドツーエンド（Read + Reason + Write）：**

```bash
python app/agent_e2e.py
```

---

## ディレクトリ構成

```
langchain-kg-agent/
├── README.md
├── docker-compose.yml      # Neo4j（APOC付き）+ Ollama
├── .env.example            # 環境変数テンプレート
├── requirements.txt
├── data/
│   ├── customers.csv       # 顧客・プラン・サポートチームのサンプルデータ（10件）
│   └── tickets.csv         # サポートチケットのサンプルデータ（15件）
└── app/
    ├── build_kg.py         # サンプルデータ投入スクリプト
    ├── agent_read.py       # SupportAgentWithKG（Readパターン）
    ├── agent_langchain.py  # LangChain Tool + AgentExecutor
    └── agent_e2e.py        # CustomerSupportAgent（エンドツーエンド）
```

---

## 注意事項

- `llama3.2` モデルはFunction Calling（Tool Use）に対応していますが、他のOllamaモデルは非対応の場合があります。モデルを変更する場合は `ollama show <model>` で確認してください。
- クラウドLLM（Claude、GPT-4等）を使う場合は各スクリプト内のコメントを参照してください。
- `.env` ファイルはGitにコミットしないでください（`.gitignore` に追加を推奨します）。
