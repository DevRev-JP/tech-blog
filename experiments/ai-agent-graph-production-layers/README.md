# ai-agent-graph-production-layers

第3部記事の **手を動かす用** experiment です。

- **記事**（なぜ分けるか・本番での置き方）: [5種類のグラフは1つのDBに入らない——本番のレイヤー設計](../../articles/ai-agent-graph-production-layers.md)
- **ここ（README）**: 何を確認するか、どのコマンドをどの順で叩くか、画面のどこを見れば「できた」と言えるか

架空の障害 **INC-001**（製品 Acme Search、顧客 Globex Corp）だけを題材にします。  
**他 experiment（`kg-puzzle-agent` / `formal-layer` / `kg-no-rag` 等）は不要**です。このディレクトリだけで完結します。

---

## この experiment でやること（3つだけ）

終わったあと、次の3文を自分の言葉で言えるようになれば成功です。  
スコープは **正確な情報の渡し方** と **5種類の使い分け** までです（アクション実行の正しさまでは扱いません。詳細は下の「まとめ」）。

| # | 言えるようになること | 確認コマンド | 画面で見る場所 |
|---|---------------------|-------------|----------------|
| **G2** | 同じ障害でも、問いが変わると **効くグラフの種類** が変わる | `scenario` | S1〜S5 と末尾の `=== 確認 — scenario ===` |
| **G1** | **MD を読む AI** と **グラフを読む AI** で答えが変わる | `agent` | Q6 / Q7 / Q4 の A（MD）と B（グラフ） |
| **G3** | **全部 Neo4j だけ**だと類似・集計の fact が弱く、層を分けると戻る（タイトルの看板） | `agent` の **Q5** | A / B / **C**（C が出るのが看板） |

補助（LLM 不要）: `compare` で 8 問の ◎/▲/✗ を一覧できます。理論の深掘りは記事側です。

```
あなたはいまここ
  setup     … データを用意する
  scenario  … G2 を確認する
  agent     … G1 + G3 を確認する（本丸）
  compare   … 精度表で復習する（任意）
```

---

## 前提（最初にそろえるもの）

| もの | 用途 | なくても動くか |
|------|------|----------------|
| Docker または Podman | Neo4j / Qdrant | 不可（`setup` に必要） |
| Python 3.11+ | CLI | 不可 |
| [Ollama](https://ollama.com/) + `gemma2:2b` | `agent` の LLM 回答 | `scenario` / `compare` だけなら不要。`agent` はコンテキスト差だけ表示される |
| Ollama + `nomic-embed-text` | Q2 の意味的類似（Qdrant） | 無いと疑似ベクトルに落ち、Q2 は「意味的類似」にならない |

**ポート**: Neo4j `7474`/`7687`、Qdrant `6333`。他 experiment の Neo4j と **同時起動不可**です。競合したら先にそちらを `compose down` してください。

**所要時間の目安**: 初回セットアップ 5〜15 分、`scenario` 数十秒、`agent`（4問・Ollama）数分、`compare` 数十秒。

---

## 手順（読者向け・迷子にならない一本道）

リポジトリのルートから、次を **上から順に** 実行してください。途中で飛ばさないでください。

### 0. 環境を用意する

```bash
# 別ターミナル（agent をやる場合）
ollama serve
ollama pull gemma2:2b
ollama pull nomic-embed-text

# この experiment
cd experiments/ai-agent-graph-production-layers
cp env.sample .env
pip install -r requirements.txt   # 推奨: python3 -m venv .venv && source .venv/bin/activate
```

`.env` の既定値（変更しなくてよい）: Neo4j ユーザー `neo4j` / パスワード `password`。

### 1. `setup` — データを入れる

**目的**: Neo4j・Qdrant を起動し、障害 INC-001 の seed を流し込む。ここをやっていないと後続は失敗します。

```bash
./run_demo.sh setup
```

**正しくできたか**

- エラーなく終わる
- ブラウザで http://localhost:7474 が開ける（認証: `neo4j` / `.env` のパスワード）

失敗したら → [トラブルシューティング](#トラブルシューティング)

---

### 2. `scenario` — G2（5種類は覚える一覧ではない）

**目的**: 1件の障害を S1→S5 の順に辿り、第1部の5種類が **別の問い・別の制御** に効くことを見る。LLM は不要です。

```bash
./run_demo.sh scenario
```

**画面の見方**

| ステップ | 種類 | 問い | 正しいときに見えること |
|---------|------|------|------------------------|
| S1 | [1] ナレッジグラフ | 顧客は？ | `顧客=Globex Corp` |
| S2 | [2] タスクグラフ | 調査の前提は？ | タスクが `─必要→` でつながる |
| S3 | [3] DAG | 実行順は？ | `実行結果: fetch_context → route_layer → generate` |
| S4 | [4] ワークフロー | 承認・差し戻しは？ | approve / reject / submit の矢印 |
| S5 | [5] ステート | 今どの段階？ | `phase=done` など現在地 |

末尾に必ず出ます:

```text
=== 確認 — scenario ===
S1 [1]KG    : ...
...
→ 同じ障害でも、場面ごとに別の種類のグラフが効いている
```

**合否**: 上の表の「見えること」と、末尾 `=== 確認 ===` が出ていれば G2 クリア。  
**まだ言えないこと**: 「1つの DB に入らない」（それは次の G3）。

---

### 3. `agent` — G1 + G3（本丸）

**目的**

1. **G1**: 同じ問いを、MD 断片（A）とグラフ（B）で AI に聞き、答えが変わること
2. **G3**: Q5 だけ **C. Neo4j単体** も出し、「全部1つの Graph DB」だと fact が弱くなること

```bash
./run_demo.sh agent
```

既定の問い順: **Q6 → Q7 → Q5 → Q4**（変えなくてよい）。

Ollama が止まっているとき:

```text
※ Ollama 未起動 — コンテキストの差は表示、LLM 回答はスキップ
```

→ 渡している文字列の差は見えます。G1/G3 の「AI の答え」まで見るなら `ollama serve` してから再実行してください。

#### 各問いの合否（傾向で判定）

LLM の文言はモデルで多少変わります。**傾向**が合えば合格です（下表。モデル例: `gemma2:2b`）。

| 問い | ゴール | A. MD断片 | B. グラフ（層分離） | C. Neo4j単体 |
|------|--------|-----------|-------------------|--------------|
| **Q6** 同一顧客か？ | G1 | 「断定できない」系 | 「はい」＋ SAME_AS 根拠 | （出ない） |
| **Q7** 昇格30分前は？ | G1 | 「断定できない」系 | リリース／レイテンシ等を列挙 | （出ない） |
| **Q5** P0 トップ製品は？ | **G3** | 「断定できない」系 | SQLite 集計（例: Acme Search=2）で答えられる | fact が弱い（件数1など）→ 断定しづらい |
| **Q4** guest は見てよいか？ | G1 | チケット内容に触れる（漏洩寄り） | 権限なしで遮断（「断定できない」等） | （出ない） |

**G3 の見方（迷子になりやすいポイント）**

- Q5 だけ **A / B / C の3段** が出ます。C が出ない場合は既定問いが古い可能性があります（この README の既定は Q5 込み）。
- **B と C で渡している数字・結論が違う** → 「1つの DB だけでは足りない」と分かる状態です。
- Q7 は Neo4j だけで足りる例です。全部を分けろ、という意味ではありません。

末尾:

```text
=== 確認 — agent ===
...
看板: Q5 でグラフ1つ vs 層分離の差も LLM 回答で見える
```

**合否**: Q6/Q7/Q4 で A≠B、Q5 で B≠C（または B の fact が C より具体的）なら G1+G3 クリア。

---

### 4. `compare` — 精度表で復習（任意・LLM 不要）

**目的**: 8問を ◎/▲/✗ で一覧する。`agent` の予習・復習用。Ollama は不要です。

```bash
./run_demo.sh compare
```

**画面の見方**

1. **セクション A**（ファイル vs グラフ）: ファイル側が ▲/✗、グラフ（分離）が ◎ に寄る
2. **セクション B**（Neo4j単体 vs 分離）: **差が出る主戦場は Q2 と Q5**（看板）。Q7 は両方 ◎（分けなくてよい例）

例（seed 固定・再現性が高い）:

| 問い | Neo4j単体 | 分離 |
|------|-----------|------|
| Q2 類似障害 | `['INC-001']` だけになりがち | `INC-00042`, `INC-00017` |
| Q5 P0 集計 | Acme Search が **1** 件側 | Acme Search **2** + Platform Logging **1** |

末尾の `=== 確認 — compare ===` が出れば実行成功です。

---

### 5. 通しでやる場合

```bash
./run_demo.sh full
```

中身は `scenario` → `agent` → `compare` です。初めてなら **手順 1→2→3 をバラで** やった方が、どこで詰まったか分かりやすいです。

---

## 中身の地図（スクリプトの裏で何が起きているか）

CLI は結果まで一気に進めます。迷子になったら、この地図だけ見れば十分です。論理の「なぜ」は記事側です。

### `agent` 1問あたりの流れ

```
問い (例: Q6)
   │
   ├─ A. mode=file
   │     fragments.json をまるごとプロンプトに載せる
   │     → Edge 型なし → LLM は断定しづらい／漏れうる
   │
   ├─ B. mode=routed（段階2・層分離）
   │     問いの型で物理層を選ぶ
   │       Q6 → Neo4j SAME_AS
   │       Q7 → Neo4j Event+BEFORE
   │       Q5 → SQLite GROUP BY
   │       Q4 → Neo4j CAN_READ（無ければ本文を渡さない）
   │       Q2 → Qdrant 類似
   │     → 型付き fact だけ渡す → LLM は根拠つきで答えやすい
   │
   └─ C. mode=neo4j_only（段階1）※ Q2 / Q5 だけ
         全部 Neo4j から無理に取る
         → 類似・集計の fact が弱い／ずれる → 回答も弱くなりやすい
```

LangGraph 上は毎回同じ3ノードです。

```
retrieve_context → route_layer → generate
       │                │            │
   コンテキスト組立   どのグラフが効くか   Ollama 回答
```

差が出るのは **generate の前に渡す文字列** だけです。モデルを賢くしているのではなく、読むものを変えています。

### なぜ Q5 だけ C が出るか

| 比較 | 確認したいこと | 使う問い |
|------|----------------|----------|
| A vs B | MD → グラフ（G1） | Q4 / Q6 / Q7（＋Q5 の A/B） |
| B vs C | グラフ1つ → 層分離（G3・看板） | **Q5**（と compare の Q2） |

Q7（時間軸）は Neo4j の Event 鎖で足りるので、C を出しても B と同じ ◎ になります。看板の「入らない」例としては弱いので、既定の C は Q5 に寄せています。

### `scenario` の流れ

```
S1 Neo4j KG traversal
S2 Neo4j TASK_PREREQUISITE
S3 LangGraph DAG エッジ一覧
S4 Neo4j WF_TRANSITION（循環）
S5 LangGraph state.phase
```

1件の障害に、5種類のグラフを当てはめています。LLM は使いません。

### 実行中のナレーション

`scenario` / `agent` / `compare` は、各ステップの直前に短い説明を出します。  
「成功すると〜」「A が〜なら成功」と書いてある行だけ追えば、合否の判断ができます。

---

## 完了チェック（読者用）

全部終わったら、次を自分に聞いてください。

- [ ] G2: 「同じ INC-001 でも、S1〜S5 で効くグラフの種類が違う」と説明できる
- [ ] G1: 「MD だと断定できない／漏れる。グラフだと根拠つき／遮断される」と、Q6 か Q4 の例で言える
- [ ] G3: 「Q5 で Neo4j単体(C)と層分離(B)の fact が違う。だから物理層を分ける」と言える
- [ ] （任意）`compare` のセクション B で Q2/Q5 の差を指差しできる

論理の整理・本番6層・OSS 選定は **記事** を読んでください。

---

## まとめ：この experiment で言ってよいこと

ここまでで十分なスコープです。チケット更新や外部 API 呼び出しなど、**世界を変えるアクション**までは扱いません。

### 言ってよいこと

- エージェントに渡すのは Markdown の全文ではなく、**型のついた事実（グラフから取った fact）** にできる
- そうすると、同じ LLM でも **根拠つきの答え** や **推測・漏洩の抑制** が起きやすい（`agent` の A vs B）
- 第1部の **5種類のグラフ** は暗記用の一覧ではなく、障害対応の **場面ごとに使い分ける**（`scenario` の S1〜S5）
- 「グラフなら何でも Neo4j 1つ」ではなく、類似や集計など **問いの型で物理層を分ける** と、渡す事実の精度が上がる（`agent` の Q5 や `compare` の Q2/Q5）

一言でいうと、**正確な情報をエージェントにどう渡すか**と、そのために **5種類のグラフをどう使い分けるか** を体験する、がこの experiment のゴールです。

### ここでは言わないこと（記事や別デモの範囲）

- グラフに従ってチケットを更新する、承認を実行する、など **アクションそのものの正しさ**
- 本番6層フル構成や write-time enrichment の運用

「判断材料が正確になる」まではこのディレクトリで確認できます。「正確なアクションを取れる」までは、この experiment の主張ではありません。

---

## コマンド早見（迷ったとき）

| コマンド | 何のため | 必須？ |
|---------|----------|--------|
| `setup` | コンテナ起動 + seed | **必須（最初に1回）** |
| `scenario` | G2 | **必須** |
| `agent` | G1 + G3 | **必須**（LLM 推奨） |
| `compare` | 精度表 | 推奨 |
| `full` | 上3つの連続 | 任意 |
| `guide` | この体験の短い案内 | 任意 |
| `stage0` / `stage1` / `stage2` | 段階ごとのデバッグ | 任意 |
| `graphs` | Edge 型の一覧（開発用） | 任意 |
| `stage0` / `stage1` / `stage2` | 段階ごとのデバッグ | 任意 |

```bash
./run_demo.sh setup
./run_demo.sh scenario
./run_demo.sh agent
./run_demo.sh compare
```

---

## 第1部・第2部との対応（参照用）

実装の対応表です。体験の本筋は上の手順です。

**第1部 5種類** → `scenario` の S1〜S5（Neo4j の型付き Edge + LangGraph）

| 種類 | Edge / 実行 |
|------|------------|
| ナレッジグラフ | `AFFECTS`, `OWNED_BY` |
| タスクグラフ | `TASK_PREREQUISITE` |
| DAG | LangGraph 固定有向エッジ |
| ワークフロー | `WF_TRANSITION` |
| ステートグラフ | `state.phase` |

**第2部 6特殊化** → 主に `compare` / `agent` の Q1〜Q8

| ID | 質問 | 物理層 |
|----|------|--------|
| Q1 | 顧客は？ | Neo4j KG |
| Q2 | 類似の過去障害は？ | Qdrant |
| Q3 | 影響範囲は？ | Neo4j `BLOCKS` |
| Q4 | 見てよいか？ | Neo4j `CAN_READ` |
| Q5 | P0 トップ製品は？ | SQLite |
| Q6 | 同一顧客か？ | Neo4j `SAME_AS` |
| Q7 | 昇格30分前は？ | Neo4j `:Event` |
| Q8 | このターンのノードは？ | コンテキスト部分グラフ |

---

## トラブルシューティング

| 症状 | 確認すること |
|------|----------------|
| ポート 7474 が使用中 | 他 experiment の Neo4j を止める |
| `setup` で Neo4j 接続失敗 | 30 秒待って `./run_demo.sh setup` を再実行 |
| Qdrant 接続失敗 | `docker compose ps` または `podman compose ps` で qdrant が Up か |
| `agent` で回答がスキップ | `ollama serve` と `ollama pull gemma2:2b` |
| Q2 の類似がおかしい | `ollama pull nomic-embed-text` のあと `./run_demo.sh setup` |
| Q5 で C（Neo4j単体）が出ない | 既定は Q6,Q7,Q5,Q4。手動なら `python app/demo_agent.py --qids Q5` |

Neo4j Browser: http://localhost:7474（`neo4j` / `.env` のパスワード）

---

## ディレクトリ（ざっくり）

```
ai-agent-graph-production-layers/
├── README.md                 ← いま読んでいる手順
├── run_demo.sh               ← エントリポイント
├── compose.yaml              ← Neo4j + Qdrant
├── env.sample                ← cp して .env に
├── data/                     ← seed（fragments / cypher / qdrant / sqlite）
└── app/                      ← scenario / agent / compare の実装
```

---

## 関連記事

- [第1部: 5種類のグラフ](https://zenn.dev/knowledge_graph/articles/ai-agent-five-graph-types)
- [第2部: グラフ特殊化](https://zenn.dev/knowledge_graph/articles/ai-agent-graph-specialization)
- [第3部: 本番レイヤー設計](https://zenn.dev/knowledge_graph/articles/ai-agent-graph-production-layers)（論理はこちら）
