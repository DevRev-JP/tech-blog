# KG（ナレッジグラフ）と RAG（ベクトル検索）の比較実験

このディレクトリは、「RAG なしで始めるナレッジグラフ QA」のコンパニオン実装です。記事で述べた理論を、実際に Docker で動作確認できます。

**記事**: https://zenn.dev/knowledge_graph/articles/kg-no-rag-starter

---

## 🎯 実験の目的

RAG（ベクタ検索）を使わず、**ナレッジグラフだけで論理的に答える**最小構成を、Docker だけで動かして確認する。

差分・否定・経路・カウントなど、**RAG が失敗しやすい問い**で、**KG（Cypher/SPARQL）が正確**に答えられることを手元で再現できます。

### 💡 設計意図：LLM を意図的に使わない理由

この実装では **LLM を使っていません**。代わりに以下の構成になっています：

- **KG パイプライン**: 質問 → Cypher クエリ（手書き） → グラフ実行 → 回答
- **RAG パイプライン**: 質問 → ベクトル埋め込み（sentence-transformers） → Qdrant 検索 → キーワード抽出 → 回答

**なぜか？** — **データストア（グラフ vs テキスト）の本質的な特性の違い** を明確にするため。

現実のシステムでは、RAG パイプラインの後ろに LLM（GPT など）がついて、検索結果から自然な回答を生成します。しかし、その LLM では以下が改善できません：

1. **差分操作** — ベクトル検索で得た曖昧なテキスト群から、正確な差分を生成できない
2. **経路追跡** — グラフの多段階関係（A → B → C）をテキスト検索では見落とす
3. **論理的否定** — 「持たない」という条件は、テキスト検索結果から推論困難

**つまり**：LLM を追加しても、データストアの根本的な限界は超えられません。だからこそ、構造化知識（KG）が必要なのです。

### 💰 エンジニアリング・リソースの観点：長期的投資

RAG は確かに「プロンプト調整」「検索パラメータ調整」「リランキング」などで精度を上げられます。しかし、以下の課題があります：

| 観点 | RAG（ベクトル検索） | KG（グラフ構造） |
|------|------------------|-----------------|
| **初期構築** | 低い（ドキュメント集めるだけ） | 高い（知識体系化が必要） |
| **精度向上** | 継続的な調整が必要 | 構造確定後は安定 |
| **埋め込みモデル変更時** | 全データ再処理必須 | 影響なし |
| **LLM 変更時** | プロンプト再調整必須 | 影響なし |
| **スケーリング** | ベクトル検索が重くなる | クエリ実行時間が線形増加 |
| **知識更新** | ドキュメント追加・修正で対応 | スキーマ拡張で対応 |

**長期的視点**：
- **RAG**: embedding モデル `sentence-transformers/v1` → `v2` → `v3` へ進化するたび、全データ再処理・再チューニング
- **KG**: embedding は関係なく、グラフスキーマと Cypher クエリは安定

**規模が大きくなる場合** — Wikidata（8,800万エンティティ）や DBpedia（480万エンティティ）の規模に到達すると、RAG のベクトル検索は計算コスト（メモリ・レイテンシ）が爆増。一方、KG は Cypher クエリで高速検索可能。

**結論**：初期段階では RAG が低コストで効く。しかし、**エンジニアリング・リソースを長期的に効かす** なら、KG への投資が ROI が高い。理想は「クエリが KG で答えられるなら KG を使い、探索が必要なら RAG を補助」という運用。

---

## 📋 実験の構成

### グラフ構造

```
Acme --[BUILDS]--> Acme Search --[HAS_FEATURE]--> Semantic Index
                                |                 Realtime Query
                                |
                                +--[REGULATES]--> POL-001, POL-002

Globex --[BUILDS]--> Globex Graph --[HAS_FEATURE]--> Semantic Index
                                  |                 Policy Audit
                                  |--[DEPENDS_ON]-> Acme Search
                                  |
                                  +--[REGULATES]--> POL-002
```

### ノード

- `Company`: Acme, Globex
- `Product`: Acme Search, Globex Graph
- `Feature`: Semantic Index, Realtime Query, Policy Audit
- `Policy`: POL-001（Personal Data Protection）, POL-002（AI Model Governance）

### 関係

- `BUILDS`: 企業が製品を構築
- `HAS_FEATURE`: 製品が機能を持つ
- `REGULATES`: ポリシーが製品を規制
- `DEPENDS_ON`: 製品が他の製品に依存

---

## 📊 試験データセット

### 5 項目版（デフォルト）

```json
{"id":"d1","text":"Acme Search は検索体験を革新。特に Semantic Index を備え、超低遅延の Realtime Query を提供します。"}
{"id":"d2","text":"Globex Graph はグラフ指向の製品で、Semantic Index を搭載、コンプライアンスに配慮した Policy Audit 機能も。"}
{"id":"d3","text":"AI Model Governance（POL-002）はデータ統合プロダクトに関連します。統合されたシステムではガイドライン適用あり。"}
{"id":"d4","text":"Personal Data Protection（POL-001）は主にユーザデータの保護観点で Acme Search を対象としています。"}
{"id":"d5","text":"Globex Graph は Acme Search の技術に依存している部分があり、相互運用性が高い。"}
```

**特徴**: 自然言語で曖昧・冗長。ベクトル検索がどこで失敗し、KG がなぜ正確か実証可能。

### 50 項目版

`docs-50.jsonl` として提供。同じドメインを様々な表現で繰り返し記述。スケール依存性を実証します。

---

## ❓ 5 つの試験問い

| ID | 型 | 問い | 期待値 | KG（5） | RAG（5） | KG（50） | RAG（50） |
|----|----|------|--------|--------|---------|----------|-----------|
| **Q1-集合** | 集合 | Acme が提供する全ユニークな機能は？ | Realtime Query, Semantic Index | ✅ | ✅ | ✅ | ❌ |
| **Q2-差分** | 対比 | Acme Search と Globex Graph の機能の違いは？ | A: Realtime Query, B: Policy Audit | ✅ | ❌ | ✅ | ❌ |
| **Q3-経路** | 経路 | Globex Graph を規制するポリシーは？ | POL-002 | ✅ | ❌ | ✅ | ❌ |
| **Q4-否定** | 否定 | Semantic Index を持たない機能は？ | Policy Audit, Realtime Query | ✅ | ❌ | ✅ | ❌ |
| **Q5-交差** | 交差 | Acme と Globex の共通機能は？ | Semantic Index | ✅ | ✅ | ✅ | ❌ |

**解釈**:
- **Q1, Q5** — RAG も小規模で正解可能（ベクトル検索が有効）
- **Q2, Q3, Q4** — RAG は常に失敗（差分・経路・論理否定はベクトル検索に不向き）
- **50 項目でいっそう悪化** — ノイズが増えるとベクトル検索の精度が急落

---

## 🚀 クイックスタート

### 前提

- macOS（または Linux/WSL2）
- Docker / Docker Compose v2
- `curl` コマンド

### 実行（5 項目版）

```bash
cd experiments/kg-no-rag

# ダウンロード済みの場合
docker compose down -v
docker compose up --detach
sleep 45

# 評価実行
curl -s http://localhost:8000/eval | jq '.'
```

**期待される結果**:
```json
{
  "summary": {
    "kg_correct": 5,
    "kg_total": 5,
    "rag_correct": 2,
    "rag_total": 5
  }
}
```

### 実行（50 項目版）

```bash
# クリーンアップ
docker compose down -v

# 50項目版で起動
export DOCS_FILE=docs-50.jsonl
docker compose up --detach
sleep 45

# 評価実行
curl -s http://localhost:8000/eval | jq '.'
```

**期待される結果**:
```json
{
  "summary": {
    "kg_correct": 5,
    "kg_total": 5,
    "rag_correct": 0,
    "rag_total": 5
  }
}
```

---

## 📁 ファイル構成

```
.
├── docker-compose.yml       # コンテナ構成（Neo4j + Qdrant + API）
└── app/
    ├── main.py              # FastAPI アプリケーション
    ├── seed.py              # DB初期化（DOCS_FILE環境変数対応）
    ├── seed.cypher          # Neo4j グラフ初期化スクリプト
    ├── questions.json       # 試験問い定義
    ├── docs.jsonl           # デフォルト: 5項目版
    ├── docs-50.jsonl        # 50項目版（別途ダウンロード）
    └── .gitignore           # Python キャッシュ除外
```

---

## 🔧 API エンドポイント

### `/ask/kg?q=<質問>`

ナレッジグラフ（Neo4j）で質問に答えます。

```bash
curl "http://localhost:8000/ask/kg?q=Acme%20が提供する全ユニークな機能は%3F"
```

### `/ask/rag?q=<質問>`

RAG（Qdrant）で質問に答えます。

```bash
curl "http://localhost:8000/ask/rag?q=Acme%20が提供する全ユニークな機能は%3F"
```

### `/eval`

すべての試験問いについて KG と RAG の精度を比較します。

```bash
curl "http://localhost:8000/eval" | jq '.'
```

---

## 📊 比較結果の解釈

### KG の強み

1. **スケール不変性** — データが 5 件でも 50 件でも、Cypher クエリの結果は同じ
2. **論理厳密性** — 集合、差分、否定、経路追跡を正確に実行
3. **構造理解** — ドメイン知識をグラフ構造として記述すれば、複雑な関係も明確に表現可能

### RAG の限界

1. **スケール依存性** — データが増えるとベクトル検索のノイズが増加
2. **操作的な問い** — 差分、否定、カウント、経路追跡は得意でない
3. **曖昧性** — テキストが増えるほど意図を正確に拾いづらくなる

---

## 💡 よくある質問

**Q: RAG を使うべきではないのか？**

A: いいえ。KG と RAG は補完関係です。本実験は「KG が得意とする領域を明確にするため、敢えて KG 単独での動作を検証」しています。実務では、ユーザーの問いが KG で答えられるか、RAG で探索すべきかを自動判定し、適切に組み合わせることが重要です。

**Q: カスタムデータで試したい場合は？**

A: `docs.jsonl` を編集または置き換え、`seed.py` を再実行してください。環境変数 `DOCS_FILE` で別ファイルを指定することも可能です。

**Q: Neo4j の ブラウザで手動確認したい場合は？**

A: `http://localhost:7474` にアクセス。認証情報は `neo4j`/`password`。

---

## 🔗 参考資料

- **記事**: [RAG なしで始めるナレッジグラフ QA——コンテナで再現する比較検証](https://zenn.dev/knowledge_graph/articles/kg-no-rag-starter)
- **Neo4j ドキュメント**: https://neo4j.com/docs/
- **Cypher チュートリアル**: https://neo4j.com/docs/cypher-manual/
- **Qdrant**: https://qdrant.tech/

---

※ この実装は記事とともに進化します。最新版は GitHub で確認してください。
