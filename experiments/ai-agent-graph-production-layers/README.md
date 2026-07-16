# ai-agent-graph-production-layers

第3部記事の再現用 experiment です。

- **記事**（問いごとの読み方）: [5種類のグラフは1つのDBに入らない——本番のレイヤー設計](../../articles/ai-agent-graph-production-layers.md)
- **この README**: 起動手順と、画面で何を見ればよいか

題材は架空の障害 **INC-001**（製品 Acme Search、顧客 Globex Corp）だけです。他 experiment は不要です。

---

## 前提

| もの | 用途 |
|------|------|
| Docker または Podman | Neo4j / Qdrant |
| Python 3.11+ | CLI |
| [Ollama](https://ollama.com/) + `gemma2:2b` | `agent` の LLM 回答（無くてもコンテキスト差は表示） |
| Ollama + `nomic-embed-text` | 類似障害（Q5）のベクトル検索 |

**ポート**: Neo4j `7474`/`7687`、Qdrant `6333`。他 experiment の Neo4j と同時起動しないでください。

---

## 手順

```bash
# 別ターミナル（agent / 類似検索をやる場合）
ollama serve
ollama pull gemma2:2b
ollama pull nomic-embed-text

cd experiments/ai-agent-graph-production-layers
cp env.sample .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

./run_demo.sh setup
./run_demo.sh scenario   # 障害を第1部5種で辿る（LLM 不要）
./run_demo.sh compare    # Q1〜Q8 の精度表（LLM 不要）
./run_demo.sh agent      # 同じ問いを MD / グラフで LLM に渡す
```

`.env` の既定: Neo4j ユーザー `neo4j` / パスワード `password`。

---

## コマンドと合否

### `setup`

Neo4j・Qdrant を起動し、seed を投入します。

- エラーなく終わる
- http://localhost:7474 が開ける（`neo4j` / `.env` のパスワード）

### `scenario`

1件の障害を S1→S5 で辿ります。LLM は不要です。

| ステップ | 見えること |
|---------|------------|
| S1 顧客は？ | `顧客=Globex Corp` |
| S2〜S5 | 問いごとに効くグラフの種類が変わる |

末尾に `=== 確認 — scenario ===` が出れば完了です。

### `compare`

Q1〜Q8 について、ファイルとグラフの精度を並べます。AI は使いません。

| 問い | ファイル側の目安 | グラフ側の目安 |
|------|------------------|----------------|
| Q1 顧客は？ | ▲ 推測 | ◎ Globex Corp |
| Q2 同一顧客か？ | ▲ 推測 | ◎ same_customer: True |
| Q3 見てよいか？ | ✗ 不可 | ◎ False（遮断） |
| Q4 影響範囲は？ | △ 叙述 | ◎ Search API |
| Q5 類似障害は？ | ▲ キーワード | ◎ INC-00042, INC-00017 |
| Q6 P0 トップ製品は？ | ✗ 不可 | ◎ Acme Search: 2 など |
| Q7 昇格30分前は？ | ✗ 不可 | ◎ リリース／レイテンシ |
| Q8 見せてよいエンティティは？ | ▲ 断片名 | ◎ INC-001 ほか固定 |

セクション B では、**類似障害（Q5）と件数集計（Q6）** で Neo4j 単体と層分離の差が出ます。時間軸（Q7）はどちらも ◎ です。

### `agent`

同じ問いを、A（MD 断片）と B（層分離のグラフ）で LLM に渡します。類似障害と件数集計では C（Neo4j 単体）も出ます。

| 問い | A（MD）の目安 | B（グラフ）の目安 | C |
|------|---------------|-------------------|---|
| Q1〜Q4, Q7〜Q8 | 曖昧・漏れ・不可寄り | 根拠つき／遮断 | 出ない |
| Q5 類似障害 | キーワード断片 | 過去障害 ID | 取りこぼし |
| Q6 P0 集計 | 断定できない | SQLite の件数 | 件数ずれ |

Ollama 未起動時はコンテキスト差だけ表示されます。回答まで見るなら `ollama serve` のあと再実行してください。

---

## トラブルシュート

| 症状 | 対処 |
|------|------|
| Neo4j に繋がらない | `./run_demo.sh setup` を再実行。ポート競合なら他 compose を down |
| 類似障害の結果がおかしい | `ollama pull nomic-embed-text` のあと `./run_demo.sh setup` |
| agent で LLM 回答が出ない | `ollama serve` と `ollama pull gemma2:2b` |
| Podman で compose 失敗 | `COMPOSE="podman compose" ./run_demo.sh setup` |

---

## ディレクトリ

```
app/           CLI と層実装
data/          fragments.json / incident.cypher / seed
compose.yaml   Neo4j + Qdrant
run_demo.sh    エントリポイント
```

補助コマンド: `graphs`（Edge 型の一覧）、`stage0` / `stage1` / `stage2`（層ごとの切り口）。
