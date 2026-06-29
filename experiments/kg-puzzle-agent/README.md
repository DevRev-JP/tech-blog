# kg-puzzle-agent

記事 [LLMに巨大パズルを解かせるな](../../articles/kg-puzzle-agent-langgraph.md) の **手を動かす用** experiment です。

架空案件 **Project Alpha**（担当チーム移管・顧客X の予算変更）を題材に、**課題 → 設計 → コマンド → こう動けば成功** の順で Part0〜2 を体感できます。設計思想の比喩は記事、再現手順は本 README に集約しています。

**SaaS 連携の PoC ではありません**（Jira / Slack / MCP は未接続。断片は JSON 直渡し、グラフは Neo4j seed）。

---

## 体験の全体像

| Part | こんな課題 | だからこう設計する | 実行 | 成功の目安 |
|------|-----------|-------------------|------|-----------|
| **0** | 断片が矛盾すると AI が推測で決め打ちする | 正式関係を **グラフに固定** し、食い違いは **聞き返す** | `./run_demo.sh compare` | A=Team B 寄り / B=Team A 固定 / Q3=確認質問 |
| **1** | プロンプト禁止でも秘匿情報が断片に混ざる | **地図を先に取得**し、権限は **辿る段階** で遮断 | `./run_demo.sh quick` | guest=Deal 未到達 / tanaka=予算可 |
| **2** | 「なぜ800万？」に全員同じ説明ができない | **SSOT + as-of + 視点** で時点と役割を切る | `./run_demo.sh part2` | monday=500のみ / today=800+矛盾 / history=500→800 |

**初回おすすめ**: 下の [クイックスタート](#クイックスタート) → `quick`（Part0+1、約1〜2分）→ 余裕があれば `part2`（十数分）。

---

<a id="クイックスタート"></a>

## クイックスタート

```bash
# 別ターミナルでホスト Ollama（Mac は Metal 利用）
ollama serve
ollama pull gemma2:2b
ollama pull nomic-embed-text   # Part2 のみ必須

cd experiments/kg-puzzle-agent
cp env.sample .env
pip install -r requirements.txt   # .venv 可（run_demo.sh が自動検出）

./run_demo.sh setup
./run_demo.sh quick      # Part0 + Part1（初回おすすめ）
# ./run_demo.sh part2    # 時系列デモ（ingest あり・十数分）
# ./run_demo.sh full     # Part0〜2 通し
```

| コンポーネント | どこで動くか |
|----------------|-------------|
| Neo4j | Docker / Podman（`compose.yaml`） |
| Ollama | **ホスト**（`ollama serve`。11434 はコンテナと競合しないよう注意） |

**前提**: Docker または Podman、Python 3.11+、ポート `7474` / `7687`（他 experiment の Neo4j と同時不可）。

---

<a id="part0"></a>

## Part0 — 断片の矛盾を推測で決めない

### 課題

Jira に「Team B 主担当」、Slack に「Team A はサポートのみ」… **どれも嘘とは限らないが、並べると矛盾する**。Skill 風の **断片直渡し** だと AI が古い方を採りやすく、**黙って確定** しがちです。

### 設計

| 経路 | やり方 | 狙い |
|------|--------|------|
| **A: 断片直渡し** | `tool_fragments.json` をプロンプトに貼るだけ | 現場の RAG / ツール合成に近い |
| **B: グラフ** | Neo4j で `Project Alpha -[:OWNED_BY]-> Team A` を固定 | 正式関係を LLM の前に渡す |
| **Q3** | グラフの現行 fact と新規断片を突合 → **確認質問** | 推測で潰さず人に聞く |

### 実行

```bash
./run_demo.sh compare    # Part0 のみ（Q1 + Q2 + Q3）
# ./run_demo.sh clarify  # Q3 だけ再実行
```

### こう動けば成功

| 質問 | A（断片） | B（グラフ） |
|------|----------|------------|
| **Q1** 断片が揃う | Team A（正答しやすい） | Team A + 根拠表示 |
| **Q2** 現場混在 | **Team B になりやすい** | **Team A に固定** |
| **Q3** 矛盾 | 黙って片方に寄る | 確認テンプレ + LLM が断定せず聞き返し |

Q3 で見る表示（`compare` 末尾 or `clarify`）:

1. `グラフ（現行）: Project Alpha -[:OWNED_BY]-> Team A`
2. 新規断片に Team B（Jira 古ドラフト）
3. 「現行の正はどちらですか？」

各 script 末尾の **`=== 確認 — … ===`** がチェックリストです。

---

<a id="part1"></a>

## Part1 — 秘匿情報は「答えるな」ではなく「渡さない」

### 課題

「社外秘を答えるな」とプロンプトで禁止しても、**断片に秘匿予算（800万）が含まれていれば** LLM が漏らしうる。質問者が **ゲスト** と **社内ユーザー** で見える範囲が違う。

### 設計

1. **LangGraph** で `retrieve_context`（グラフ取得）→ `generate`（回答）の順。**地図を先に** 渡す。
2. **権限**はパストラバーサル（グラフを辿ってノードを集める）の段階で効かせ、ゲストは Deal ノードに **到達しない**。

| ユーザー | experiment 上の ID | 見える範囲 |
|----------|-------------------|-----------|
| 社内 | `user_tanaka` | Project Alpha + **Deal（顧客X・秘匿予算）** |
| ゲスト | `user_guest` | Deal **以前** で遮断（コンテキスト空） |

### 実行

```bash
./run_demo.sh quick     # Part0 + 権限デモ
./run_demo.sh part1     # + LangGraph エージェント単体
```

### こう動けば成功

| 比較 | 断片 + 禁止指示 | グラフ + guest |
|------|----------------|----------------|
| 「予算は？」 | 800万が漏れうる | **取得段階で遮断**（コンテキスト空） |

`demo_permissions.py` / `agent_langgraph.py` の末尾 **`=== 確認 — … ===`** を参照。

---

<a id="part2"></a>

## Part2 — 「月曜は500万だったよね？」に同じ基準で答える

### 課題

1週間で **500万 → 800万**、10月リリース予定、営業とエンジニアの **前提の食い違い** が発生。Skill に「最新の800万」だけ書いても、**なぜ500万が無効か** は説明できない。

### 設計（3ステップ）

| ステップ | やること |
|----------|----------|
| **1. 記録**（Graphiti ingest） | 週次エピソード（YAML）からファクトをグラフに載せる（LLM） |
| **2. 正本の決定**（SSOT） | `temporal_rules` で valid_at / invalid_at を確定（LLM 非依存） |
| **3. 検索**（as-of + 視点） | **いつの時点**か（`monday` / `today`）・**誰の立場**か（`sales` / `eng`）を指定して有効ファクトだけ返す |

**ポイント**: ステップ1はモデル依存ですが、**失効・正本はステップ2の SSOT が決定論的に上書き** するため、デモの骨格は安定します。

### 実行

```bash
./run_demo.sh part2              # ingest + SSOT + search + history（DB リセットあり）

# 取込済みなら検索だけ（数秒）
./run_demo.sh part2-search monday
./run_demo.sh part2-search today
./run_demo.sh part2-search sales    # 営業視点
./run_demo.sh part2-search eng      # エンジニア視点
```

### こう動けば成功

| preset | 時点 | 見えるもの |
|--------|------|-----------|
| `monday` | 6/23 | **500万のみ**（10月予定なし） |
| `today` | 6/28 | **800万** + 10月予定 + **⚠ 未解決矛盾** |
| `sales` | 6/28・営業 | 800万・再稟議（エンジニア見積は除外） |
| `eng` | 6/28・エンジニア | 3人月・矛盾（営業 Slack は除外） |

**history** 末尾: `500万（06/23〜06/25） → 800万（06/25〜現在）` の変遷。

**search 出力の例**（`today`）:

```
▸ search  2026-06-28 · 全体
  ・…予算を800万円まで拡大可能…
  ・…本番リリース目標は2026年10月中旬
  ⚠ 未解決: …800万前提と整合しない
```

詳細ログ: `DEMO_VERBOSE=1 ./run_demo.sh part2`

---

## コマンド早見表

| やりたいこと | コマンド | 目安時間 |
|-------------|----------|---------|
| 初回セットアップ | `setup` | 数分（モデル pull 含む） |
| **おすすめ初回体験** | `quick` | 1〜2 分 |
| Part0 のみ | `compare` | 数十秒 |
| Part2 フル | `part2` | 十数分 |
| Part0〜2 通し | `full` | 十数分 |
| 手順を1ステップずつ | `guide` | — |
| Part2 検索だけ | `part2-search <preset>` | 数秒 |

preset: `monday` | `friday` | `today` | `sales` | `eng` | `manager`

---

## 設定の要点

| 設定 | デフォルト | いつ変えるか |
|------|-----------|-------------|
| `OLLAMA_LLM_MODEL` | `gemma2:2b` | Part2 で ingest が崩れるとき（**非推奨**: `qwen2.5:3b` は 800万未抽出の run あり） |
| `OLLAMA_GRAPHITI_MODEL` | 同上 | Part2 だけ別モデルにしたいとき |
| `DEMO_VERBOSE` | `0` | Graphiti の内部ログを見たいとき `1` |
| `NEO4J_PASSWORD` | `env.sample` 参照 | 初回 `cp env.sample .env` 後 |

**なぜ gemma2:2b か**: 公式 `ollama pull` のみで Part0〜2 が Mac ホスト Ollama で完走し、Part2 の invalid_at 体験が安定するため（他モデルの実測は [付録: モデル選定](#appendix-models)）。

---

<a id="demo-vs-production"></a>

## PoC と本番の線引き（要点のみ）

| 見えるもの | この PoC | 本番で足すもの |
|-----------|---------|---------------|
| 断片取得 | JSON 直渡し | Jira/Slack MCP、RAG |
| グラフ検索 | Project Alpha **固定** | エンティティ解決、GraphRAG |
| LangGraph | 2 ノードのみ | 矛盾分岐、HITL |
| Q3 矛盾検出 | 正規表現突合 | ingest / スキーマ / ワークフロー |
| Part2 | Graphiti + SSOT + CLI | 運用ガバナンス、Slack UI |
| マルチプレイヤー | **再現しない** | Claude Tag 型の共有 @Claude |

コード内の `[デモ]` / `DEMO_SSOT` / `[デモ固定]` は上記の簡略化です。記事後半の「地図の基盤」（権限・as-of・視点・矛盾・根拠）は Part1/2 で CLI 体験できます。

---

<a id="troubleshooting"></a>

## うまくいかないとき

| 症状 | 確認・対処 |
|------|-----------|
| Neo4j に繋がらない | `setup` 後 45 秒待つ。ポート 7474/7687 の競合 |
| Ollama エラー | `curl http://localhost:11434/api/tags`。他 experiment の Ollama コンテナを停止して `ollama serve` |
| Part2 でファクト 0 件 | `.env` の `OLLAMA_LLM_MODEL=gemma2:2b` を確認。`setup` でモデル pull |
| Neo4j Browser が空 | Part2 実行後は **静的グラフ用 Cypher は 0 件**（意図どおり）。[付録: Neo4j](#appendix-neo4j) |
| 警告ログが多い | デフォルトは抑制。`DEMO_VERBOSE=1` はデバッグ時のみ |

---

## データファイル

| ファイル | 役割 |
|----------|------|
| `data/tool_fragments.json` | Part0 断片（Q1/Q2/Q3） |
| `data/project_alpha.cypher` | Part0/1 静的グラフ |
| `data/temporal_episodes.yaml` | Part2 エピソード + SSOT + as-of preset |

---

<a id="appendix-models"></a>

## 付録: モデル選定（Part2 デバッグ用）

Part0/1 はモデル差が小さい。**Part2（Graphiti 構造化抽出）だけ** 差が出ます。

| モデル | Part2 invalid_at 体験 | 備考 |
|--------|----------------------|------|
| **gemma2:2b**（採用） | ✅ 完走 | 公式 pull のみ・約52秒 |
| gemma-2-2b-jpn-it | ✅ | community GGUF（HF 経由） |
| qwen2.5:3b | ❌ run により 800万未抽出 | 非推奨 |

SSOT ルール（`temporal_rules.yaml`）の骨格:

| ルール | 意味 |
|--------|------|
| budget_500 | 6/23 有効 → **6/25 失効** |
| budget_800 | 6/25〜現在有効 |
| eng_budget_conflict | 未解決矛盾（⚠ 出力） |

`.env` で `OLLAMA_LLM_MODEL` を変えたら `./run_demo.sh part2` を再実行。

---

<a id="appendix-neo4j"></a>

## 付録: Neo4j Browser

http://localhost:7474 — 認証 `neo4j` / `.env` の `NEO4J_PASSWORD`

**どの Cypher を使うか**

| 直前のコマンド | DB の中身 | 使うクエリ |
|---------------|----------|-----------|
| `quick` / `seed`（Part2 **未**実行） | Part0/1 静的グラフ | 下記 Part0/1 |
| `part2` / `full` | Graphiti グラフ | 下記 Part2 |

**Part0/1**（`quick` 直後）:

```cypher
MATCH (u:User {id: 'user_tanaka'})-[:MEMBER_OF]->(:Team)-[:HAS_ACCESS_TO]->(p:Project)
OPTIONAL MATCH (p)-[r]-(n) WHERE n:Team OR n:TechStack OR n:Deal
RETURN p, r, n;
```

**Part2**（`part2` 直後・予算ファクト）:

```cypher
MATCH ()-[e:RELATES_TO]->()
WHERE e.fact CONTAINS '500' OR e.fact CONTAINS '800' OR e.fact CONTAINS '整合'
RETURN e.fact, e.valid_at, e.invalid_at
ORDER BY e.valid_at;
```

`valid_at` / `invalid_at` が 500→失効、800→現在有効なら SSOT 生效。CLI の `part2-search today` と突き合わせてください。

---

## 関連記事

- [ツールを100個並べてもAIエージェントは賢くならない](../../articles/kg-agent-skill-layer.md)
- [Claude の外側にコンテキストグラフを置くと…](../../articles/context-graph-improves-llm.md)
- [LLMに巨大パズルを解かせるな](../../articles/kg-puzzle-agent-langgraph.md)（本記事）
