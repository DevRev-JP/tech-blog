# kg-puzzle-agent

記事 [LLMに巨大パズルを解かせるな：ナレッジグラフで「正解の絵」を渡すエージェント設計](../../articles/kg-puzzle-agent-langgraph.md) の再現用 experiment です。

**SaaS 連携の PoC ではありません。** Jira / Slack / Confluence / MCP サーバーは **接続していません**。断片は JSON をプロンプトに直渡しし、グラフは Neo4j に seed した固定データです。比較対象は「Skill **相当**（断片合成）」vs コンテキストグラフ（BFF 層）です。

**記事との役割分担**: 記事は設計思想と比喩を説明します。再現手順・コマンド・期待出力・SSOT・トラブルシュートは **本 README** に集約しています。

<a id="demo-vs-production"></a>

## デモと現実の差（必読）

エンジニアが **そのまま本番コードと誤認しない** よう、experiment で **実際に動いているもの** と **本番で別途必要なもの** を分けて書きます。設計思想（地図を LLM の前に置く・権限は取得段階・時系列は SSOT・矛盾は聞き返す）は本番向きですが、**実装の多くは最小 PoC 用のショートカット** です。

| 見え方・用語 | experiment の実装 | 本番で置き換えるもの | 誤解しないで |
|--------------|-------------------|----------------------|--------------|
| **Skill / MCP**（Part0 A） | `tool_fragments.json` を **プロンプトに貼るだけ**。ツール選定・MCP プロトコル・並列取得なし | Jira/Slack/Confluence MCP、RAG、エージェントのツールルーティング | **MCP を動かしているわけではない** |
| **グラフ検索**（Part0 B / Part1） | 質問からエンティティは **Project Alpha 固定**（`graph_retriever.py`） | エンティティリンク、GraphRAG、LLM→Cypher、全文+グラフ | 権限付き Cypher の **形** は本物、**クエリ解釈** は簡略 |
| **LangGraph**（Part1） | `retrieve_context → generate` の **2 ノードのみ**。分岐・HITL なし | 矛盾時の `clarify` 分岐、Human-in-the-loop、チェックポイント | **順序（地図→回答）** が学びの核心 |
| **Q3 矛盾検出** | `OWNED_BY` と断片を **正規表現** で突合（`conflict_clarify.py`） | ingest パイプライン、スキーマ制約、承認ワークフロー、Graphiti invalidation | **聞き返す流れ** は本番パターン、**検出ロジックは教材レベル** |
| **Q3 聞き返し文** | 決定論テンプレ + Ollama **1 プロンプト**（LangGraph 非経由） | Slack スレッド返信、LangGraph 分岐、チケット起票 | UI レイヤは未実装 |
| **Part2 Graphiti ingest** | 本物の Graphiti + Ollama。抽出結果は **モデル依存** | 本番 LLM、監査ログ、再 ingest ポリシー | ingest は本物に近い |
| **Part2 SSOT** | `temporal_rules.yaml` を ingest 後に Neo4j へ書き戻し。不足時は `DEMO_SSOT` で **MERGE 補完** | Git 管理の運用ルール、DataOps、承認済み canonical fact | **時系列の正を LLM 任せにしない** 思想は本番向き。`DEMO_SSOT` は **デモ完走用の補完** |
| **Part2 議論用行** | 固定文言（`demo_temporal.py` の `[デモ固定]` テンプレ） | Q3 と同型の LLM 聞き返し or 人間ファシリテーション | **未解決矛盾の可視化** が目的。Slack UI ではない |
| **マルチプレイヤー / Claude Tag** | 記事の **設計議論のみ**。CLI 単一セッション | Slack 連携、共有 @Claude、会話追跡 | experiment では **再現しない**（明記済み） |

**本番への写像（Part ごと）**

| Part | experiment で確認できること | 本番で自分で足すこと |
|------|----------------------------|----------------------|
| **0** | 断片推測 vs 確定関係；矛盾時は聞き返し | 実 MCP/RAG；本番用矛盾検出；LangGraph 分岐 |
| **1** | 権限付きパストラバーサル；地図→回答の順 | エンティティ解決；複数ノードのエージェント |
| **2** | Graphiti ingest + SSOT + as-of + 視点；根拠チェーン | 運用 SSOT のガバナンス；HITL；Slack 等 UI |

コード内の `[デモ]` / `DEMO_SSOT` / コメントも同じ線引きです。不明点は該当 `app/*.py` を開いて確認してください。

**マルチプレイヤー（記事後半）との関係**: 記事では [Claude Tag](https://www.anthropic.com/news/introducing-claude-tag) 等を例に、Slack チャンネル内の **共有 @Claude**（複数人で1エージェント）にも触れています。**本 experiment では Slack 連携・チャンネル会話の追跡・複数人の同時操作は再現しません**（CLI の単一セッション）。代わりに、マルチプレイヤーに必要な **地図の基盤** を Part1/2 で最小限体験できます。Skill だけでは、権限・時系列・視点・未解決矛盾をチーム全員と共有 AI が同じ座標系で参照するのが難しい、という論点の **素材** です（記事の「1人1AIから、チーム会議の中のAIへ」を参照）。

| 地図の基盤 | 本 experiment での確認方法 |
|------------|------------------------------|
| **権限**（人ごとに見える範囲） | Part1: `user_tanaka` / `user_guest`（`./run_demo.sh quick`） |
| **as-of**（いつ時点の「正」か） | Part2: `./run_demo.sh part2-search monday` / `today` |
| **視点**（営業 vs エンジニア） | Part2: `./run_demo.sh part2-search sales` / `eng` |
| **未解決矛盾** | Part2: `./run_demo.sh part2` または `part2-search today`（出力の ⚠ セクション） |
| **根拠チェーン** | Part2: `./run_demo.sh part2` 末尾の `history` |
| **矛盾→確認** | Part0 Q3: `compare` 末尾 / `python app/conflict_clarify.py` |

<a id="map-foundation"></a>

## TL;DR

```bash
# 1. ホスト Ollama（Mac では Metal/GPU 利用 — コンテナより高速）
ollama serve          # 別ターミナル
ollama pull gemma2:2b             # LLM（Ollama 公式、約1.6GB）
ollama pull nomic-embed-text    # 埋め込み（Part2 のみ必須）

# 2. Python 依存インストール（venv は任意 — 自分の環境に合わせて）
cd experiments/kg-puzzle-agent
cp env.sample .env
pip install -r requirements.txt   # または: python3 -m venv .venv && source .venv/bin/activate && pip install ...
# ※ .venv を作った場合、run_demo.sh は activate 不要で自動検出します

# 3. Neo4j + デモ
./run_demo.sh setup
./run_demo.sh quick    # 約1〜2分（Part0 + 権限。初回おすすめ）
# ./run_demo.sh full     # フル体験（十数分）
```

## 構成

| コンポーネント | 実行場所 | 理由 |
|----------------|----------|------|
| **Neo4j** | Docker または Podman (`compose.yaml`) | 再現性・セットアップ簡略化 |
| **Ollama** | **ホスト** | Mac で GPU（Metal）が使える |

`run_demo.sh` は `docker compose`（優先）または `podman compose` を自動選択します。環境変数 `COMPOSE` で上書き可能（例: `COMPOSE="podman compose" ./run_demo.sh setup`）。

**メモリ**: LLM は **`gemma2:2b` 1 本だけ** 使う（約 1.6GB + Part2 時の embed 約 0.3GB）。不要モデルは `ollama stop <name>`。

## なぜ LLM は `gemma2:2b` か（必読）

デフォルトは **Ollama 公式 library** の Google Gemma 2 2B（`ollama pull gemma2:2b`）です。

選定の優先順位は次のとおりです。

1. **`ollama pull` だけ** — community GGUF や HF エイリアスは使わない
2. **Part0〜2 が Mac + ホスト Ollama で十数分以内に完走** すること
3. **Part2 の invalid_at 体験**（500万失効 → 800万有効 → 除外リスト → history）が通ること

実測環境: Mac 24GB RAM、Ollama 0.30.x、Neo4j は Docker/Podman、LLM はホスト Metal 推論（2026-06）。

### 通しテスト結果（Part0 → Part1 → Part2）

| モデル | 取得 | Part0 | Part1 | Part2 | invalid_at 体験 | Part2 search の厚み |
|--------|------|-------|-------|-------|-----------------|---------------------|
| **gemma2:2b** | 公式 `ollama pull` | 約3秒 | 約4秒 | **約52秒** | ✅ 完走 | 800万+再稟議+3ヶ月（SSOT 含む **4件前後**） |
| gemma-2-2b-jpn-it（community GGUF） | HF 経由 | 約3秒 | 約5秒 | 約61秒 | ✅ 完走 | 800万+再稟議+3ヶ月 **4件** |
| qwen2.5:3b | 公式 | 約5秒 | 約5秒 | 約46秒 | ❌ 800万未抽出の run あり | 有効ファクト 0件の run あり |
| qwen3:4b | 公式 | 約21秒 | — | 遅い／未完 | — | Graphiti 多段呼び出しが重い |
| qwen3.5:4b | 公式 | 約43秒 | — | 空応答で失敗 | — | thinking + json_schema と相性悪い |
| sarashina2.2-3b（community） | HF 等 | 約4秒 | — | 約2.8分 | △ パイプラインは通る | 予算ファクトほぼ取れず |
| sarashina2.2-1b | HF 等 | — | — | — | — | Ollama 0.30 で起動不可 |

**採用理由**: 公式 `gemma2:2b` は qwen2.5:3b より Part2 抽出が安定し、community 版と同程度に invalid_at デモが通る。かつ **`ollama pull gemma2:2b` のみ** で済む。

### Part0 / Part1 — モデル差は小さい

- **compare**: 断片直渡し vs グラフの A/B は、gemma2:2b / qwen2.5:3b とも正答（Team A / Python + Neo4j）
- **part1**: tanaka は Alpha 可、guest は拒否 — どのモデルでも同一。LangGraph も問題なし

Part0・Part1 だけなら qwen2.5:3b でも足ります。**差が出るのは Part2（Graphiti 構造化抽出）** です。

### Part2 — 3 段パイプラインと SSOT

Part2 だけ LLM 任せにすると、小モデルは `invalid_at` が付かない・800万ファクトが生まれないことがあります。この experiment では次の 3 段に分けています。

```
[1] Graphiti ingest（Ollama LLM） … エピソードからファクトを抽出
[2] SSOT 適用（temporal_rules）   … valid_at / invalid_at を確定（LLM 非依存）
[3] as-of クエリ（Neo4j 直接）    … **today（2026-06-28）** 時点で有効／失効を表示
```

ingest 直後に `./run_demo.sh part2` 内で `temporal_episodes.yaml` の `temporal_rules` を Neo4j に書き戻します。**500/800 を含むファクトが 1 件でも ingest されていれば**、SSOT が invalid_at を確定し、search / history はグラフ上の時系列をそのまま見せます。

| SSOT ルール | valid | invalid | 意味 |
|-------------|-------|---------|------|
| budget_500（「500」含む） | 06/23 | **06/25** | 月曜エピソード。水曜で失効 |
| budget_800（「800」含む） | 06/25 | 現在有効 | 水曜エピソード。`canonical_fact` で文言も正規化 |
| reapproval（「再稟議」含む） | 06/25 | 現在有効 | 水曜エピソード。未抽出時は `canonical_fact` を MERGE |
| eng_3months（「3ヶ月」含む） | 06/26 | 現在有効 | 木曜エピソード |
| oct_release_target（「10月中旬」等） | 06/26 | 現在有効 | 木曜。**将来予定**（2026年10月中旬リリース） |
| eng_budget_conflict（「整合」「3人月」） | 06/27 | 現在有効 | 金曜。**未解決矛盾**（営業800万 vs エンジニア試算） |

**公式 gemma2:2b で期待できる search 出力（代表例）**:

```
=== 結論（2026-06-28 時点で有効なファクト） ===
・山田部長は予算を800万円まで拡大可能とのこと
・Project Alpha 拡張（顧客X）の本番リリース目標は2026年10月中旬

=== 将来予定（グラフ上の計画 — 未到来のマイルストーン） ===
・Project Alpha 拡張（顧客X）の本番リリース目標は2026年10月中旬

=== なぜ800万か（グラフの根拠） ===
1. 2026-06-23「顧客Xの予算は500万円」 → invalid: 2026-06-25
2. 2026-06-25「山田部長は予算を800万円まで拡大可能とのこと」 → 現在有効

=== 検索結果から除外されたもの ===
・「顧客Xの予算は500万円」— invalid_at: 2026-06-25
```

**qwen2.5:3b で失敗した run の例**（同じ SSOT でも ingest に 800 が無いと救えない）:

- SSOT: `budget_800: 0件`
- search: 「現在有効なファクトが見つかりませんでした」
- 抽出ファクトに中国語混じり（`顧客X的预算是500万日元…`）が出ることも

### Part2 でもっと詳しく追いたい場合

デフォルト `gemma2:2b` でも SSOT により **800万・再稟議・3ヶ月** は search に載ります。来期跨ぎなど **SSOT 未登録のファクト** は ingest 品質に依存します。

| 変更 | Part2 で増えやすい情報 | トレードオフ |
|------|------------------------|--------------|
| 日本語 IT 版 community GGUF（例: Google [`gemma-2-2b-jpn-it`](https://huggingface.co/google/gemma-2-2b-jpn-it) の HF 変換） | エピソード由来の細かい文言・来期跨ぎ等（実測: search **4件以上**） | **Ollama 公式 library ではない**。HF pull + エイリアスが必要 |
| より大きい公式モデル（例: `gemma2:9b`） | エピソード由来ファクト全体 | VRAM・Part2 時間増 |
| qwen2.5:3b | — | 速いが **800万未抽出でデモが崩れる run あり**（非推奨） |

`.env` の `OLLAMA_LLM_MODEL`（Part2 だけ別なら `OLLAMA_GRAPHITI_MODEL` も）を変えて `./run_demo.sh part2` を再実行してください。SSOT による invalid_at の骨格はモデルに依存しません。

### その他の補足

- **LLM は 1 本、埋め込みは `nomic-embed-text`（Part2 のみ）**。2 モデル同時ロードは VRAM の無駄。
- Graphiti の `max_tokens=16384` はライブラリ推奨のまま（短縮は `OLLAMA_GRAPHITI_MAX_TOKENS`）。
- Ollama 公式の `gemma2:2b` は **汎用 Gemma 2 2B** で、Ollama library に **日本語 IT 版（jpn-it）は載っていない**。日本語特化を使う場合は上表の community 行のとおり HF 経由になる。

モデルを変える場合は `.env` の `OLLAMA_LLM_MODEL` を変更してください。

Ollama をコンテナで動かすと Mac 上では CPU 推論になり、Graphiti ingest などが遅くなります。**11434 はホスト `ollama serve` 専用**です（`compose.yaml` に Ollama サービスはありません）。

他 experiment（`kg-ollama` / `hands-on-kg-builder` 等）の Ollama コンテナが 11434 を占有していると `./run_demo.sh` は起動時にエラーになります。先にそのコンテナを停止してから `ollama serve` を起動してください。

## 前提

- Docker（`docker compose` v2+）または Podman 5.x（Neo4j のみ）
- ホスト Ollama（`ollama serve`）
- Python 3.11+
- ポート `7474` / `7687` — 他 experiment の Neo4j と同時起動不可

## ストーリー（Part0〜2 共通）

**Project Alpha** を軸に、Part0/1 は体制・権限、Part2 は同一案件の **Project Alpha 拡張（顧客X）** の予算・工期が週次で更新される、という一続きのシナリオです。

<a id="part0"></a>

## Part0：断片直渡し（Skill 相当） vs グラフ

**目的**: 同一事実を断片（Skill **相当** — MCP 非接続）とグラフの両方で表現し、推測依存の差を体感します。A モードは **JSON をプロンプトに貼っているだけ** です（[デモと現実の差](#demo-vs-production)）。

```bash
./run_demo.sh compare   # Part0 のみ
./run_demo.sh quick     # Part0 + Part1 権限（初回おすすめ、約1〜2分）
```

Q2 の断片は **現場の混在**（Jira 古ドラフト・Slack の文脈依存発言・Confluence の未確定表記）を再現しており、「Team A/B が両方ある」のはデモの不自然さではなく、きれいに揃わないデータの例です。

| 質問 | A: 断片直渡し（Skill 相当） | B: グラフ |
|------|------------|--------|
| **Q1（同一事実）** | 断片3つを推測で統合（正答しやすい） | `Alpha -[:OWNED_BY]-> Team A` で固定 + 根拠表示 |
| **Q2（現場混在）** | 古い Jira「Team B 主担当」+ Slack「Team A はサポートのみ」等 → **Team B になりやすい** | `OWNED_BY` で **Team A** に固定 |
| **Q3（矛盾→確認）** | Q2 と同型：黙って Team B 側に寄りがち | グラフ vs 新規断片を **正規表現で突合**（[デモと現実の差](#demo-vs-production)）→ 確認テンプレ + LLM 聞き返し |

**Q2 断片の中身**（`data/tool_fragments.json` の `trap_question`）:

| ソース | 内容（要約） |
|--------|----------------|
| Jira ALPHA-102（古ドラフト） | 主担当は Team B。移管予定。 |
| Slack #team-a | Team A は Alpha のサポート要員のみ。 |
| Confluence 最新版 | 正式決定は別途。 |

> Q1 だけだと両方正答しやすいです。Q2 で「きれいでない断片」のとき推測依存の差が体感しやすくなります。

**矛盾時の確認**: 断片直渡しだけだと AI は黙ってどちらかを選びがちです（Q2 A）。KG では **Q3**（`app/conflict_clarify.py`）でグラフ上の現行 fact（Team A）と新規断片（Jira Team B）を **正規表現で突合** し、確認質問テンプレートを表示します。`compare` / `quick` の末尾で自動実行されます。

```bash
python app/conflict_clarify.py   # Q3 のみ（要 seed / compare 前後）
# または: ./run_demo.sh clarify
```

**Q3 で確認する項目**:

| # | 期待される表示 |
|---|----------------|
| 1 | `グラフ（現行）: Project Alpha -[:OWNED_BY]-> Team A` |
| 2 | `新規断片: [Jira チケット ALPHA-102（古いドラフト）] … Team B …` |
| 3 | 確認テンプレートに「現行の正はどちらですか？」 |
| 4 | **LLM 聞き返し**（Ollama 要）: Team A/B を断定せず確認質問のみ |
| 5 | Q2 Skill との対比コメント（黙って確定 vs 聞き返し） |

矛盾検出は **決定論** だが **正規表現ヒューリスティック**（本番の ingest/スキーマ検証ではない — [デモと現実の差](#demo-vs-production)）。聞き返し文はテンプレート + LLM の2段（LangGraph 分岐・Slack UI は未実装）。

Part2 の ⚠ 未解決矛盾は、推測で潰さず **チーム議論用の確認例** も search 出力に含みます。文言は **`[デモ固定]` テンプレ**（本番の LLM 聞き返しそのものではない — [デモと現実の差](#demo-vs-production)）。

各 script 末尾の **`=== 確認 — … ===`** で期待結果をチェックできます。手作業で1ステップずつ確認する場合は [手作業ガイド](#手作業で一つずつ確認) のステップ 2 を参照してください。

<a id="part1"></a>

## Part1：LangGraph と権限

**目的**: グラフコンテキストを LLM の **前** に渡す LangGraph エージェントと、権限をパストラバーサルで効かせる設計を体験します。**2 ノードのみ**（本番の分岐・HITL は別途 — [デモと現実の差](#demo-vs-production)）。記事後半の **マルチプレイヤー向け地図** では、同じ共有 @Claude でも **人ごとに見える範囲が違う** 前提の最小形です（[地図の基盤](#map-foundation)）。

```bash
./run_demo.sh quick     # Part0 + 権限デモ
./run_demo.sh part1     # + LangGraph エージェント
```

**権限デモ**（`demo_permissions.py`）:

1. **断片直渡し + 「社外秘を答えるな」**（Skill 相当・MCP 非接続）: 断片に秘匿予算（800万）が含まれていれば LLM が漏らしうる
2. **グラフ + user_guest**: パストラバーサル時点で到達不能 → コンテキスト自体が空

`user_tanaka` は Alpha（と Deal）に到達します。`user_guest` は **最初から見えません**。権限はプロンプトではなく **取得段階** で効かせます。

実装の全文: [app/](./app/)（エントリ `retrieve_context` → `generate`）。手作業は [手作業ガイド](#手作業で一つずつ確認) のステップ 3〜4。

<a id="part2"></a>

## Part2：時系列と as-of

**目的**: 2026年6月第4週の予算・工期更新（500万 → 800万 → 10月予定 → エンジニア矛盾）を Graphiti + SSOT + as-of クエリで扱い、**なぜ800万か** を根拠チェーンで説明します。ingest は本物に近い一方、`DEMO_SSOT` による MERGE 補完と `[デモ固定]` 議論用行は **デモ完走用**（[デモと現実の差](#demo-vs-production)）。`sales` / `eng` 視点と未解決矛盾は、記事後半の **チーム会議内 AI** に必要な地図素材です（Slack 共有操作そのものは再現しません。[地図の基盤](#map-foundation)）。

```bash
./run_demo.sh part2
# 取込済みなら as-of / 視点だけ再実行:
./run_demo.sh part2-search monday
./run_demo.sh part2-search today
./run_demo.sh part2-search sales
./run_demo.sh part2-search eng
./run_demo.sh full      # Part0〜2 通し（十数分）
```

Part2 は **ingest → SSOT → as-of クエリ**（+ **視点フィルタ**）の3段構成です。詳細ログは `DEMO_VERBOSE=1 ./run_demo.sh part2` または `./run_demo.sh --verbose part2`。

**search 出力イメージ**（`./run_demo.sh full` 実行時のコンパクト表示の例）:

```
▸ search  2026-06-28 · 全体
  ・山田部長は Project Alpha 拡張（顧客X）の予算を800万円まで拡大可能とのこと
    2026-06-25〜現在有効 · sales-update-wednesday
  ・Project Alpha 拡張（顧客X）の本番リリース目標は2026年10月中旬
    2026-06-26〜現在有効 · eng-estimate-thursday
  …
  ⚠ 未解決: 800万予算枠では最小3人月を確保できず、営業提示の800万前提と整合しない
```

**history** では `500万（06/23〜06/25） → 800万（06/25〜現在）` の変遷と置換理由を表示します。Neo4j Browser 用 Cypher は [Neo4j Browser（30秒ツアー）](#neo4j-browser30秒ツアー) を参照してください。

## Part 対応（一覧）

| Part | コマンド | 見るポイント |
|------|----------|--------------|
| 0 | `compare` / `quick` | Q1 同一事実 A/B、**Q2 現場混在**、**Q3 矛盾→確認** |
| 1 | `quick` / `part1` | **秘匿予算の Skill 漏洩** vs グラフ遮断、LangGraph |
| 2 | `part2` | as-of **monday/today**、**10月予定**、視点差、未解決矛盾、history |

| 導線 | コマンド | 所要時間（目安） |
|------|----------|------------------|
| 初回おすすめ | `./run_demo.sh quick` | 1〜2 分 |
| 詳細ログ | `./run_demo.sh --verbose part2` または `.env` で `DEMO_VERBOSE=1` | デバッグ時のみ |
| 手作業ガイド | `./run_demo.sh guide` | — |
| フル体験 | `./run_demo.sh full` | 十数分 |
| Part2 だけ再検索 | `./run_demo.sh part2-search monday` 等 | 数秒 |

## 手作業で一つずつ確認

`./run_demo.sh full` は Part0〜2 を一括実行します（Part0 の重複なし・Part2 はコンパクト表示）。デフォルトでは Graphiti の警告ログは抑えられます。詳細は `DEMO_VERBOSE=1`、**ステップを分けて**確認したい場合は `./run_demo.sh guide` を参照してください。

```bash
./run_demo.sh guide    # 全手順をターミナルに表示
```

| ステップ | コマンド | 確認すること |
|----------|----------|--------------|
| 0 | `./run_demo.sh setup` | Neo4j / Ollama / モデル |
| 1 | `./run_demo.sh seed` | Neo4j Browser で Project Alpha グラフ |
| 2 | `./run_demo.sh compare` | Q2: A=Team B, B=Team A · Q3: 確認質問テンプレート |
| 3 | `python app/demo_permissions.py` | Skill 800万漏洩 vs guest 遮断 |
| 4 | `python app/agent_langgraph.py` | グラフ → 回答 |
| 5 | `python app/graphiti_setup.py` | 初期化完了 |
| 6 | `python app/demo_temporal.py ingest` | SSOT 6 ルール（10月予定含む） |
| 7 | `python app/demo_temporal.py search --as-of monday` | 500万のみ（10月予定なし） |
| 8 | `python app/demo_temporal.py search --as-of today` | 800万 + **10月リリース予定** + 矛盾 + 議論用確認例 |
| 9 | `python app/demo_temporal.py history` | 500→800 変遷 |

各 script の末尾に **`=== 確認 — … ===`** セクションがあり、チェックリスト形式で期待結果を示します。

### 出力と詳細ログ（デフォルトは結果のみ）

**デフォルト**では Graphiti ingest 中の無害な警告（`EquivalentSchemaRuleAlreadyExists`、`property key does not exist` 等）は表示しません。`===` セクション・SSOT ログ・search/history の結果だけが出ます。

Graphiti 内部の stderr まで見たいとき（デバッグ）:

```bash
# 方法1: 環境変数
DEMO_VERBOSE=1 ./run_demo.sh part2

# 方法2: .env に追記
# DEMO_VERBOSE=1
```

Python を直接実行する場合も `.env` の `DEMO_VERBOSE=1` が効きます。

Part2 は **ingest → SSOT → as-of クエリ（+ 視点フィルタ）** です。成功の目安:

| preset | as-of | 見えるもの |
|--------|-------|-----------|
| `monday` | 2026-06-23 | 500万のみ有効（**10月予定は未登場**） |
| `friday` | 2026-06-27 | 800万 + 3ヶ月見積もり + 矛盾（10月予定あり） |
| `today` | 2026-06-28 | `friday` と同じ（本日時点の最新） |
| `sales` | today / 営業視点 | 800万・再稟議（エンジニア見積もりは除外） |
| `eng` | today / エンジニア視点 | 3ヶ月・矛盾（営業Slackは除外） |
| `manager` | today / 全視点 | `today` と同じ（全ファクトが見える管理者視点） |

## Neo4j Browser（30秒ツア）

http://localhost:7474 を開き、Username **`neo4j`** / Password **`.env` の `NEO4J_PASSWORD`**（`env.sample` なら `password`）で接続します。クエリを貼ったら **Run**（Ctrl+Enter）。結果は **Table** / **Graph** タブを切り替えて確認してください。

### どの Cypher を使うか（重要）

Part2 開始時に Neo4j を **volume ごとリセット** するため、DB の中身はコマンドで変わります。

| 直前に実行したコマンド | DB の中身 | Browser で使う Cypher |
|------------------------|-----------|------------------------|
| `./run_demo.sh quick` / `part1` / `seed` | Part0/1 の **静的グラフ**（`User` / `Project` / `OWNED_BY`） | 下記 **Part0/1** |
| `./run_demo.sh part2` / `all` / `full` | Part2 の **Graphiti グラフ**（`Entity` / `Episodic` / `RELATES_TO`） | 下記 **Part2** |

> **`all` 直後に Part0/1 の Cypher を実行すると 0 件** になります（意図どおり）。Part0 の完成図を見たいときは `./run_demo.sh seed` のあと Part0/1 用を実行するか、`part2` を走らせない `./run_demo.sh quick` の直後に Browser を開いてください。

### Part0/1 — Project Alpha の完成図

**前提**: `./run_demo.sh quick` または `./run_demo.sh seed` の **後**（Part2 未実行）。

```cypher
MATCH (u:User {id: 'user_tanaka'})-[:MEMBER_OF]->(:Team)-[:HAS_ACCESS_TO]->(p:Project)
OPTIONAL MATCH (p)-[r]-(n) WHERE n:Team OR n:TechStack OR n:Deal
RETURN p, r, n;
```

**Graph タブ**: `Project`・`Team A`・`Python + Neo4j`・`Deal（顧客X）` が `OWNED_BY` / `USES` / `HAS_ACCESS_TO` でつながって見えれば OK です。

### Part2 — 予算ファクトの valid / invalid

**前提**: `./run_demo.sh part2` または `./run_demo.sh all` の **後**（ingest + SSOT 済み）。

**まず DB にデータがあるか確認**（左サイドバーと同じ目安）:

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC LIMIT 10;
```

**`gemma2:2b` で `./run_demo.sh all` 直後の実測例**（2026-06-28 時点）:

| label | n |
|-------|---|
| Entity | 16 |
| Episodic | 4 |

左サイドバーは **Nodes (20)** / **Relationships (22)** 前後、`Entity`・`Episodic`・`Community`・`Saga`、`RELATES_TO` 等 — これで正常です。

**予算・矛盾ファクト（README 掲載クエリ）**:

```cypher
MATCH ()-[e:RELATES_TO]->()
WHERE e.fact CONTAINS '500' OR e.fact CONTAINS '800' OR e.fact CONTAINS '整合'
RETURN e.fact, e.valid_at, e.invalid_at, e.name
ORDER BY e.valid_at;
```

**Table タブの実測例**（3 行 — このクエリのフィルタどおり）:

| e.fact（要約） | e.valid_at | e.invalid_at | 意味 |
|----------------|------------|--------------|------|
| …予算は**500万**円 | 2026-06-23 | **2026-06-25** | 月曜ファクト → 水曜で失効 |
| …**800万**円まで拡大可能 | 2026-06-25 | **null** | 現在有効 |
| …800万前提と**整合**しない | 2026-06-27 | **null** | 未解決矛盾（CLI の ⚠ と同型） |

`e.name`（`HAS_CONTRACT` / `WILL_BE_EXPANDED` 等）は **Graphiti が付けた関係名** で、CLI 出力のエピソード名とは別物です。`valid_at` / `invalid_at` が上表どおりなら SSOT は効いています。

**Graph タブで部分グラフを見る**:

```cypher
MATCH (a)-[e:RELATES_TO]->(b)
WHERE e.fact CONTAINS '800' OR e.fact CONTAINS '500'
RETURN a, e, b
LIMIT 25;
```

**実測例**: `Project Alpha`・`営業`・`顧客X` の 3 ノードが `RELATES_TO` でつながる部分グラフ（全体 16 Entity の一部）。

**CLI の search に出る 10 月予定・再稲議・3 ヶ月なども見る**（フィルタを広げる）:

```cypher
MATCH ()-[e:RELATES_TO]->()
WHERE e.valid_at IS NOT NULL
RETURN e.fact, e.valid_at, e.invalid_at, e.name
ORDER BY e.valid_at;
```

ファクト文言は Graphiti 抽出 + SSOT のため **1 語句ずつ完全一致しない** こともあります。CLI の `./run_demo.sh part2-search today` と `invalid_at` の有無を突き合わせると確認しやすいです。

## データ（SSOT）

| ファイル | 内容 |
|----------|------|
| `data/tool_fragments.json` | Part0 断片（Q1 正答・**Q2 矛盾**・秘匿漏洩デモ） |
| `data/project_alpha.cypher` | Part0/1 グラフ（Deal ノード含む） |
| `data/temporal_episodes.yaml` | Part2 4エピソード + **as-of preset / 視点 / SSOT** |

## うまくいかないとき

1. **Neo4j 未起動** — `./run_demo.sh setup` 後 45 秒待つ
2. **Ollama 未起動 / コンテナ競合** — `curl http://localhost:11434/api/tags` でホスト Ollama を確認。11434 を使うコンテナがあれば停止してから `ollama serve` を起動
3. **モデル未 pull / 古い `.env`** — `grep OLLAMA_LLM_MODEL .env` が **`gemma2:2b`** か確認。`qwen2.5:3b` のままだと setup が 1.9GB の Qwen を pull し、Part2 で `budget_800: 0件` になりやすい。`cp env.sample .env` 後 `./run_demo.sh setup`
4. **Graphiti 構造化出力失敗** — `.env` で `GRAPHITI_STRUCTURED_OUTPUT_MODE=json_object`。Qwen3.5 系は `OLLAMA_DISABLE_THINKING=true`（デフォルト）
5. **Part2 のファクト文言** — Graphiti 抽出はモデル依存。ingest 後 SSOT で `invalid_at` 確定（match 0 件時は `canonical_fact` を MERGE）。search/history は **as-of（today = 2026-06-28）** で Neo4j 直接参照
6. **ログの警告** — デフォルトでは Graphiti の無害 WARN は表示されません。`DEMO_VERBOSE=1 ./run_demo.sh part2` で詳細を確認できます。Part2 末尾で search に 800 万・10 月予定・history に変遷が出れば OK
7. **Neo4j Browser が空** — [Neo4j Browser（30秒ツア）](#neo4j-browser30秒ツア) の「どの Cypher を使うか」を確認。`all` 直後は Part0 用クエリは 0 件。Part2 用を実行するか、`./run_demo.sh seed` で静的グラフを再投入

## 関連記事

- [ツールを100個並べてもAIエージェントは賢くならない](../../articles/kg-agent-skill-layer.md)
- [Claude の外側にコンテキストグラフを置くと…](../../articles/context-graph-improves-llm.md)
