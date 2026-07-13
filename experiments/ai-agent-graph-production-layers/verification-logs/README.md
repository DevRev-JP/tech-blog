# 実機検証ログ（記事掲載用）

記事 [ai-agent-graph-production-layers](../../articles/ai-agent-graph-production-layers.md) §8 に載せる **再現可能な実行ログ** を格納します。

**既存ログは上書きしません。** `./run_demo.sh verify` のたびに `verification-logs/<tag>/runs/<run_id>/` が **新規追加**され、`index.jsonl` に1行追記されます。

## 再現手順

```bash
# 前提（agent 用）
ollama serve   # 別ターミナル
ollama pull gemma2:2b
ollama pull nomic-embed-text

cd experiments/ai-agent-graph-production-layers
cp env.sample .env
pip install -r requirements.txt
./run_demo.sh setup

# ログ記録（毎回新しい runs/<run_id>/ を追記）
./run_demo.sh verify
# タグ（記事・モデル識別子）を付ける場合:
./run_demo.sh verify 2026-07-13-gemma2-2b
```

## ディレクトリ構成

```
verification-logs/
  index.jsonl                    # 全タグの実行履歴（1実行=1行・追記のみ）
  <tag>/
    index.jsonl                  # 当該タグの実行履歴
    runs/
      20260713T074053Z/         # 1回の verify = 1ディレクトリ（不変）
        manifest.json
        scenario.log
        compare.log
        agent.log
        summary.md
      20260713T120000Z/        # 再実行分は別ディレクトリ
        ...
```

| ファイル | 内容 |
|---------|------|
| `manifest.json` | 記録日時・`run_id`・LLM モデル・既定 QID・git HEAD 等 |
| `scenario.log` | G2: S1〜S5 の出力 |
| `compare.log` | 8問の ◎/▲/✗ と段階1 vs 分離 |
| `agent.log` | G1+G3: 既定問いの A/B(/C) と LLM 回答 |
| `summary.md` | 記事執筆用の要約 |

## 参照ログ（記事 §8 基準）

| タグ | run_id | 用途 |
|------|--------|------|
| [`2026-07-13-gemma2-2b`](./2026-07-13-gemma2-2b/) | [`20260713T074053Z`](./2026-07-13-gemma2-2b/runs/20260713T074053Z/) | 第3部ドラフト §8 の初回実機検証 |

実行履歴の一覧: `cat verification-logs/index.jsonl` または `jq` で閲覧。

**注意**: `agent.log` の自然文は Ollama モデルで多少変わります。記事では **コンテキストの差** と **回答の傾向** を根拠にしてください。compare のラベルと Q5/Q2 の fact は seed 固定で再現性が高いです。
