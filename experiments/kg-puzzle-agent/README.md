# kg-puzzle-agent

記事 [LLMに巨大パズルを解かせるな — ナレッジグラフで「正解の絵」を渡すエージェント設計](../../articles/kg-puzzle-agent-langgraph.md) の再現用 experiment です。

**SaaS 連携の PoC ではありません。** Jira / Slack / Confluence / MCP は接続せず、同一事実のダミーデータで Skill だけ vs コンテキストグラフ（BFF 層）の差を体験できます。

## TL;DR

```bash
# 1. ホスト Ollama（Mac では Metal/GPU 利用 — コンテナより高速）
ollama serve          # 別ターミナル
ollama pull gemma2:2b             # LLM（Ollama 公式、約1.6GB）
ollama pull nomic-embed-text    # 埋め込み（Part2 のみ必須）

# 2. Neo4j + デモ
cd experiments/kg-puzzle-agent
cp env.sample .env
pip install -r requirements.txt
./run_demo.sh setup
./run_demo.sh compare
```

## 構成

| コンポーネント | 実行場所 | 理由 |
|----------------|----------|------|
| **Neo4j** | Podman (`compose.yaml`) | 再現性・セットアップ簡略化 |
| **Ollama** | **ホスト** | Mac で GPU（Metal）が使える |

**メモリ**: LLM は **`gemma2:2b` 1 本だけ** 使う（約 1.6GB + Part2 時の embed 約 0.3GB）。不要モデルは `ollama stop <name>`。

## なぜ LLM は `gemma2:2b` か（必読）

デフォルトは **Ollama 公式 library** の Google Gemma 2 2B（`ollama pull gemma2:2b`）です。

選定の優先順位は次のとおりです。

1. **`ollama pull` だけ** — community GGUF や HF エイリアスは使わない
2. **Part0〜2 が Mac + ホスト Ollama で十数分以内に完走** すること
3. **Part2 の invalid_at 体験**（500万失効 → 800万有効 → 除外リスト → history）が通ること

実測環境: Mac 24GB RAM、Ollama 0.30.x、Neo4j は Podman、LLM はホスト Metal 推論（2026-06）。

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

- **compare**: Skill 断片 vs グラフの A/B は、gemma2:2b / qwen2.5:3b とも正答（Team A / Python + Neo4j）
- **part1**: tanaka は Alpha 可、guest は拒否 — どのモデルでも同一。LangGraph も問題なし

Part0・Part1 だけなら qwen2.5:3b でも足ります。**差が出るのは Part2（Graphiti 構造化抽出）** です。

### Part2 — 3 段パイプラインと SSOT

Part2 だけ LLM 任せにすると、小モデルは `invalid_at` が付かない・800万ファクトが生まれないことがあります。この experiment では次の 3 段に分けています。

```
[1] Graphiti ingest（Ollama LLM） … エピソードからファクトを抽出
[2] SSOT 適用（temporal_rules）   … valid_at / invalid_at を確定（LLM 非依存）
[3] as-of クエリ（Neo4j 直接）    … 金曜 2024-11-08 時点で有効／失効を表示
```

ingest 直後に `./run_demo.sh part2` 内で `temporal_episodes.yaml` の `temporal_rules` を Neo4j に書き戻します。**500/800 を含むファクトが 1 件でも ingest されていれば**、SSOT が invalid_at を確定し、search / history はグラフ上の時系列をそのまま見せます。

| SSOT ルール | valid | invalid | 意味 |
|-------------|-------|---------|------|
| budget_500（「500」含む） | 11/04 | **11/06** | 月曜エピソード。水曜で失効 |
| budget_800（「800」含む） | 11/06 | 現在有効 | 水曜エピソード。`canonical_fact` で文言も正規化 |
| reapproval（「再稟議」含む） | 11/06 | 現在有効 | 水曜エピソード。未抽出時は `canonical_fact` を MERGE |
| eng_3months（「3ヶ月」含む） | 11/07 | 現在有効 | 木曜エピソード（抽出できた場合のみ） |

**公式 gemma2:2b で期待できる search 出力（代表例）**:

```
=== 結論（2024-11-08 時点で有効なファクト） ===
・山田部長は予算を800万円まで拡大可能とのこと
・ただし来期に跨ぐ場合は再稟議が必要とのこと
・3ヶ月なら今期に収まる

=== なぜ800万か（グラフの根拠） ===
1. 2024-11-04「顧客Xの予算は500万円」 → invalid: 2024-11-06
2. 2024-11-06「山田部長は予算を800万円まで拡大可能とのこと」 → 現在有効
→ 水曜エピソード取込で月曜ファクトが invalid 化

=== 検索結果から除外されたもの ===
・「顧客Xの予算は500万円」— invalid_at: 2024-11-06
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

他 experiment（`kg-ollama` / `hands-on-kg-builder` 等）の Ollama コンテナが 11434 を占有していると `./run_demo.sh` は起動時にエラーになります。先に `podman stop kg-ollama` 等で止めてください。

## 前提

- Podman 5.x（Neo4j のみ）
- ホスト Ollama（`ollama serve`）
- Python 3.11+
- ポート `7474` / `7687` — 他 experiment の Neo4j と同時起動不可

## Part 対応

| Part | コマンド | 見るポイント |
|------|----------|--------------|
| 0 | `compare` | 同一事実・Skill 断片 vs グラフ |
| 1 | `part1` | 権限（tanaka vs guest）、LangGraph |
| 2 | `part2` | Graphiti 時系列、なぜ800万か |

Part2 は **Graphiti ingest（LLM 抽出）→ SSOT で invalid_at 確定 → as-of クエリ** の3段階です（詳細は上記「Part2 — 3 段パイプラインと SSOT」）。金曜時点で **500万は除外・800万は有効** と history の変遷が見えるのが成功の目安です。

## データ（SSOT）

| ファイル | 内容 |
|----------|------|
| `data/tool_fragments.json` | Part0 モード A 用断片 |
| `data/project_alpha.cypher` | Part0/1 グラフ（同一事実） |
| `data/temporal_episodes.yaml` | Part2 エピソード + **as-of / temporal_rules（invalid_at SSOT）** |

## うまくいかないとき

1. **Neo4j 未起動** — `./run_demo.sh setup` 後 45 秒待つ
2. **Ollama 未起動 / コンテナ競合** — `curl http://localhost:11434/api/tags` / ホストで `ollama serve`。11434 を使う Podman Ollama は停止
3. **モデル未 pull / 古い `.env`** — `grep OLLAMA_LLM_MODEL .env` が **`gemma2:2b`** か確認。`qwen2.5:3b` のままだと setup が 1.9GB の Qwen を pull し、Part2 で `budget_800: 0件` になりやすい。`cp env.sample .env` 後 `./run_demo.sh setup`
4. **Graphiti 構造化出力失敗** — `.env` で `GRAPHITI_STRUCTURED_OUTPUT_MODE=json_object`。Qwen3.5 系は `OLLAMA_DISABLE_THINKING=true`（デフォルト）
5. **Part2 のファクト文言** — Graphiti 抽出はモデル依存。ingest 後 SSOT で `invalid_at` 確定（match 0 件時は `canonical_fact` を MERGE）。search/history は **as-of（金曜）** で Neo4j 直接参照
6. **ログの警告** — `EquivalentSchemaRuleAlreadyExists` / `entity_edges` WARN / `Target entity not found` は多くの場合 **無害**。Part2 末尾で search に 800 万・history に変遷が出れば OK

## 関連記事

- [ツールを100個並べてもAIエージェントは賢くならない](../../articles/kg-agent-skill-layer.md)
- [Claude の外側にコンテキストグラフを置くと…](../../articles/context-graph-improves-llm.md)
