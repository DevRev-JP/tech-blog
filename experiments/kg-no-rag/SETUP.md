# データセット切り替え手順

このプロジェクトには、2つのデータセットバージョンがあります。

## 📊 データセット概要

### 小規模版 (5項目) - docs.jsonl
- **特徴**: 明確で矛盾のない情報
- **KG評価結果**: 5/5 ✅
- **RAG評価結果**: 2/5 (Q1, Q5のみ成功)
- **目的**: 基本動作確認、KGの基本的な優位性を示す

### 大規模版 (50項目) - docs-50.jsonl
- **特徴**: 自然で説得力のあるノイズ、エンタープライズツール15種類を追加
- **KG評価結果**: 5/5 ✅ (変わらず)
- **RAG評価結果**: 1/5 (Q2のみ成功)
- **目的**: スケール依存性を実証、KGのロバスト性を強調、RAGのノイズ耐性テスト

## 🔄 データセット切り替え方法

### 初回起動（デフォルト: 小規模版 5個）
```bash
docker compose down -v
docker compose up --detach
sleep 60
curl -s http://localhost:8000/eval | jq '.summary'
```
期待される結果: **KG: 5/5, RAG: 2/5**

### コンテナ再起動なしでデータセット切り替え

#### 現在のデータセットを確認
```bash
curl -s http://localhost:8000/dataset | jq '.'
# 出力例: {"file": "docs.jsonl", "count": 5}
```

#### 大規模版（50個）に切り替え
```bash
curl -X POST "http://localhost:8000/switch-dataset?file=docs-50.jsonl" | jq '.'
# その後、テストを実行
curl -s http://localhost:8000/eval | jq '.summary'
```
期待される結果: **KG: 5/5, RAG: 1/5**

#### 小規模版（5個）に戻す
```bash
curl -X POST "http://localhost:8000/switch-dataset?file=docs.jsonl" | jq '.'
# その後、テストを実行
curl -s http://localhost:8000/eval | jq '.summary'
```
期待される結果: **KG: 5/5, RAG: 2/5**

### 自動切り替えスクリプト
```bash
# 小規模版でテスト
./switch-dataset.sh small

# 大規模版でテスト
./switch-dataset.sh large

# 両方実行して比較
./switch-dataset.sh compare
```

## 📝 評価項目の詳細

### Q1-集合: Acme が提供する全ユニークな機能は？
- **期待**: `["Realtime Query", "Semantic Index"]`
- **小規模**: KG✅ RAG✅
- **大規模**: KG✅ RAG❌ (曖昧な情報が多すぎて該当機能が埋もれる)

### Q2-差分: Acme Search と Globex Graph の機能の違いは？
- **期待**:
  - `only_in_a`: `["Realtime Query"]`
  - `only_in_b`: `["Policy Audit"]`
- **小規模**: KG✅ RAG❌ (集合差分操作はベクトル検索に不向き)
- **大規模**: KG✅ RAG❌ (さらに失敗)

### Q3-経路: Globex Graph を規制するポリシーは？
- **期待**: `["POL-002"]`
- **小規模**: KG✅ RAG❌ (グラフの経路を追跡できない)
- **大規模**: KG✅ RAG❌ (さらに失敗)

### Q4-否定: Semantic Index を持たない機能は？
- **期待**: `["Policy Audit", "Realtime Query"]`
- **小規模**: KG✅ RAG❌ (論理的否定が曖昧)
- **大規模**: KG✅ RAG❌ (さらに失敗)

### Q5-交差: AcmeとGlobexの共通機能は？
- **期待**: `["Semantic Index"]`
- **小規模**: KG✅ RAG✅
- **大規模**: KG✅ RAG❌ (ノイズが多すぎて共通要素を特定できない)

## 🏗️ ファイル構成

```
app/
├── main.py              # FastAPI アプリケーション
├── seed.py              # データベース初期化（環境変数対応）
├── questions.json       # 評価用質問セット
├── docs.jsonl           # デフォルト: 小規模版 (5項目)
├── docs-5.jsonl         # 小規模版 (5項目)
└── docs-50.jsonl        # 大規模版 (50項目)
```

## 🔧 環境変数

### DOCS_FILE
- **デフォルト**: `docs.jsonl`
- **オプション**: `docs-5.jsonl`, `docs-50.jsonl`, カスタムファイル
- **使用箇所**: seed.py で初期化時に読み込むドキュメントファイルを指定

設定例:
```bash
export DOCS_FILE=docs-50.jsonl
docker compose up --detach
```

## 📊 比較結果サマリー

| 質問 | KG(小規模) | RAG(小規模) | KG(大規模) | RAG(大規模) |
|------|---------|---------|---------|---------|
| Q1   | ✅      | ✅      | ✅      | ❌      |
| Q2   | ✅      | ❌      | ✅      | ❌      |
| Q3   | ✅      | ❌      | ✅      | ❌      |
| Q4   | ✅      | ❌      | ✅      | ❌      |
| Q5   | ✅      | ✅      | ✅      | ❌      |
| **計** | **5/5** | **2/5** | **5/5** | **0/5** |

## 💡 重要なポイント

1. **KGの一貫性**: データサイズが増えてもKG (Neo4j + Cypher) の結果は変わらない
2. **RAGのスケール依存性**: ベクトル検索はノイズが増えると精度が低下する
3. **カテゴリ分類**:
   - `simple`: 基本的な集合操作（両方成功可能）
   - `scale_dependent`: スケールで失敗（小規模では成功）
   - `scale_stable`: スケールで安定（KGは常に成功）
   - `kg_exclusive`: KG向け（小規模ではRAGも成功）

## 🚀 使用例

### スクリプトで自動切り替え

```bash
#!/bin/bash

echo "小規模版テスト (5項目)"
docker compose down -v
docker compose up --detach
sleep 45
echo "=== 小規模版結果 (KG: 5/5, RAG: 2/5) ==="
curl -s http://localhost:8000/eval | jq '.summary'

echo ""
echo "大規模版テスト (50項目)"
docker compose down -v
DOCS_FILE=docs-50.jsonl docker compose up --detach
sleep 45
echo "=== 大規模版結果 (KG: 5/5, RAG: 0/5) ==="
curl -s http://localhost:8000/eval | jq '.summary'
```

このスクリプトで両バージョンの結果を自動で比較できます。
