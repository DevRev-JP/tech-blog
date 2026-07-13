# ai-agent-graph-production-layers

記事 [5種類のグラフは1つのDBに入らない——本番のレイヤー設計](../../articles/ai-agent-graph-production-layers.md)（第3部）の **手を動かす用** experiment です。

架空の障害 **INC-001**（製品 Acme Search、顧客 Globex Corp）を題材に、第1部の 5 種類のグラフと第2部の 6 特殊化を **1 つのディレクトリだけで** 段階 0→2 まで辿ります。

**他 experiment（`kg-puzzle-agent` / `formal-layer` / `kg-no-rag` 等）への実行依存はありません。** 完了条件は本 README のコマンドのみです。

---

## 体験の全体像

この experiment は 2 つの体験を柱にしています。

| ゴール | 体験 | コマンド | 成功の目安 |
|--------|------|---------|-----------|
| **G2** | 障害 INC-001 を第1部5種のグラフで1本の物語として辿る | **`scenario`**（LLM 不要） | S1〜S5 で 5 種が別役割だと説明できる |
| **G1** | 同じ問いを「MD を読む AI」と「グラフを読む AI」に聞き、回答差を見る | **`agent`**（Ollama） | Q6/Q7 でグラフ側だけが根拠つきで答える |

補助として、段階ごとの精度差を LLM なしで一覧する `compare`、Edge 型を確認する `graphs` があります。

| 段階 | こんな課題 | 触るもの | コマンド | 成功の目安 |
|------|-----------|---------|---------|-----------|
| **0** | MD 断片だけでは型が持てない | `fragments.json` | `stage0` / **`agent`**(file) | 推測・集計不可が出る |
| **1** | グラフ1つ(Neo4j)では fact が弱い | Neo4j のみ | `stage1` / **`agent`**(neo4j_only) | Q2/Q5 の fact がずれる |
| **2** | グラフを層分離して読む | Neo4j+Qdrant+SQLite | **`agent`**(routed) / `stage2` | 型付き fact で ◎確定 |

**初回おすすめ**: [クイックスタート](#クイックスタート) → **`scenario`** → **`agent`** → `full`

---

## この experiment のゴール

**核心は「AI に何を読ませるか」** です。DB を分ける話は、その結果として AI に渡すコンテキストの精度が変わる、という順序です。

1. **MD 断片を読む AI** — `fragments.json` をプロンプトに貼る（段階0）。Edge 型なし → 推測・漏れ
2. **グラフを読む AI** — Neo4j / Qdrant / SQLite から **型付き fact だけ** を LangGraph が取得して Ollama に渡す（段階2）
3. **グラフ1つだけ** — 全部 Neo4j から取ると、類似(Q2)・集計(Q5)の fact が弱い/ずれる（段階1）
4. **LangGraph** — `retrieve_context → route_layer → generate` の実行パイプライン（第1部のステート/DAG と同型）
5. **第1部5種** — `./run_demo.sh scenario` で 1 本の障害物語として辿る（`graphs` は Edge 型のデバッグ表示）

| 体験 | コマンド | 何が変わるか |
|------|---------|-------------|
| 第1部5種を1シナリオで辿る | **`scenario`** | 同じ障害で問いごとに効く種が変わる |
| AI が MD vs グラフを読む | **`agent`** | 渡すコンテキストと LLM 回答 |
| 精度ラベル比較（LLM不要） | `compare` | ◎/▲/✗ の一覧 |
| 5種類の Edge 型（開発用） | `graphs` | グラフの正本 |

```bash
ollama serve
ollama pull gemma2:2b          # agent の LLM 回答用
ollama pull nomic-embed-text   # Q2 の意味的類似（Qdrant 埋め込み）用
./run_demo.sh setup
./run_demo.sh scenario # G2: 第1部5種を1本の障害物語で（LLM 不要）
./run_demo.sh agent    # ← ここが本丸（G1: MD vs グラフ）
./run_demo.sh full     # scenario + agent + compare
```

> Q2（類似障害）は Ollama の `nomic-embed-text` で埋め込みを作り、Qdrant で意味的類似を引きます。Ollama がない場合は疑似ベクトルにフォールバックしますが、その場合 Q2 は「意味的類似」になりません（`setup` が警告します）。

## クイックスタート

```bash
# 別ターミナル（LLM を使う場合のみ。graphs / stage0 / stage2 の構造確認は不要）
ollama serve
ollama pull gemma2:2b          # agent の LLM 回答用
ollama pull nomic-embed-text   # Q2 の意味的類似用

cd experiments/ai-agent-graph-production-layers
cp env.sample .env
pip install -r requirements.txt   # .venv 可

./run_demo.sh setup
./run_demo.sh scenario # G2: 第1部5種を1本の障害物語で（Ollama 不要）
./run_demo.sh agent    # G1: LangGraph が MDを読む AI vs グラフを読む AI
./run_demo.sh compare  # 精度ラベル比較（Ollama 不要）
./run_demo.sh full     # scenario + agent + compare
```

| コンポーネント | どこで動くか |
|----------------|-------------|
| Neo4j | `compose.yaml`（ポート 7474 / 7687） |
| Qdrant | `compose.yaml`（ポート 6333） |
| SQLite | ホスト上 `audit.db`（コンテナ不要） |
| LangGraph | `retrieve_context → route_layer → generate`（**agent**） |
| Ollama | **agent** で LLM 回答（scenario/compare/graphs は不要） |

**前提**: Docker または Podman、Python 3.11+。他 experiment の Neo4j と **同時起動不可**（ポート競合）。

---

## コマンド一覧

```bash
./run_demo.sh setup     # コンテナ起動 + seed
./run_demo.sh scenario  # G2: 第1部5種を1本の障害物語で（LLM 不要）
./run_demo.sh agent     # G1: LangGraph + Ollama（MD vs グラフ）
./run_demo.sh compare   # 精度比較（LLM 不要）
./run_demo.sh graphs    # 第1部5種類 + Edge 型一覧（開発用）
./run_demo.sh stage0    # 段階0のみ
./run_demo.sh stage1    # 段階1のみ
./run_demo.sh stage2    # 段階2: Q1〜Q8 ルーティング
./run_demo.sh quick     # compare と同じ
./run_demo.sh full      # scenario + agent + compare
./run_demo.sh guide     # 体験の全体像
```

各 script 末尾の **`=== 確認 ===`** がチェックリストです。

---

## 第1部 5 種類（必須）

| 種類 | Edge / 実行 | 実装 |
|------|------------|------|
| ナレッジグラフ | `AFFECTS`, `OWNED_BY` | `data/incident.cypher` |
| タスクグラフ | `TASK_PREREQUISITE` | `app/layers/task_graph.py` |
| DAG | LangGraph 固定有向エッジ | `app/graphs/dag_graph.py` |
| ワークフロー | `WF_TRANSITION` | `app/layers/workflow_graph.py` + LangGraph |
| ステートグラフ | `state.phase` | `app/agent_langgraph.py` |

`./run_demo.sh scenario` は、この 5 種を障害 INC-001 の S1〜S5 として順に辿ります。YAML / Markdown を正本にしません（段階 0 の `fragments.json` は**わざと**対照用のみ）。

---

## 第2部 6 特殊化 — Q1〜Q8

| ID | 質問 | 物理層 |
|----|------|--------|
| Q1 | このチケットの顧客は？ | Neo4j KG |
| Q2 | 類似の過去障害は？ | Qdrant |
| Q3 | ログ基盤障害の影響範囲は？ | Neo4j `BLOCKS` |
| Q4 | このエージェントは見てよいか？ | Neo4j `CAN_READ` |
| Q5 | 過去 30 日 P0 トップ製品は？ | SQLite |
| Q6 | Slack とメールは同一顧客か？ | Neo4j `SAME_AS` |
| Q7 | P0 昇格の 30 分前に何が？ | Neo4j `:Event` |
| Q8 | このターンで渡したノードは？ | コンテキスト部分グラフ |

---

## ディレクトリ構成

```
ai-agent-graph-production-layers/
├── README.md
├── compose.yaml
├── run_demo.sh
├── data/
│   ├── fragments.json      # 段階0のみ
│   ├── incident.cypher     # Neo4j seed
│   ├── incident_docs.jsonl # Qdrant
│   └── audit_seed.sql      # SQLite
└── app/
    ├── agent_router.py       # LangGraph retrieve → route_layer → generate（agent）
    ├── context_builders.py   # MD断片 vs グラフ fact の組み立て
    ├── answer_paths.py       # 段階0/1/2 の回答ロジック
    ├── demo_scenario.py      # scenario コマンド（G2: 第1部5種の物語）
    ├── compare_layers.py     # compare コマンド
    ├── demo_agent.py         # agent コマンド（G1）
    ├── setup_seed.py
    ├── demo_graphs.py
    ├── stage0_fragments.py
    ├── stage1_neo4j_only.py
    ├── stage2_router.py
    ├── agent_langgraph.py    # scenario/graphs: DAG + ステート展示
    ├── graphs/dag_graph.py
    └── layers/
```

---

## 完了条件

- [ ] `./run_demo.sh scenario` → S1〜S5 で第1部5種の役割差を説明できる（G2）
- [ ] `./run_demo.sh agent` → Q6/Q7 で MD とグラフの LLM 回答差が目視できる（G1）
- [ ] `./run_demo.sh compare` → 精度差が目視できる（Ollama 不要）
- [ ] `./run_demo.sh stage2` → Q1〜Q8 がルーティング付きで答えられる
- [ ] `./run_demo.sh full` → scenario + agent + compare が連続で通る
- [ ] 本 README に他 experiment への実行依存がない

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| ポート 7474 が使用中 | 他 experiment の Neo4j を `compose down` |
| `setup` で Neo4j 接続失敗 | 30 秒ほど待って `./run_demo.sh setup` を再実行 |
| Qdrant 接続失敗 | `podman compose ps` / `docker compose ps` で qdrant が Up か確認 |

Neo4j Browser: http://localhost:7474（認証: `neo4j` / `.env` のパスワード）

---

## 関連記事

- [第1部: 5種類のグラフ](https://zenn.dev/knowledge_graph/articles/ai-agent-five-graph-types)
- [第2部: グラフ特殊化](https://zenn.dev/knowledge_graph/articles/ai-agent-graph-specialization)
- [第3部: 本番レイヤー設計](https://zenn.dev/knowledge_graph/articles/ai-agent-graph-production-layers)（本記事・ドラフト）
