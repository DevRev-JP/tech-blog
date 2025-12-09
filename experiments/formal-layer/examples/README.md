# ハンズオン例: 記事の最小構成を実際に実行する

このディレクトリには、記事のハンズオンセクションで説明されている最小構成の例を、実際に実行できる形で提供しています。

## 1. SQL（値レイヤ）の最小構成

記事の「ハンズオン：最小構成の SQL 実装」に対応する例です。

### 実行方法

```bash
cd examples/sql-minimal
npm install
npm run setup  # データベースの初期化
npm start      # サンプルクエリの実行
```

### ファイル構成

- `app.ts`: 記事で説明されている最小構成の実装
- `schema.sql`: データベーススキーマ
- `package.json`: 依存関係

## 2. KG（意味レイヤ）の最小構成

記事の「ハンズオン：Neo4j + Cypher の最小例」に対応する例です。

### 実行方法

```bash
# Neo4j を起動（Docker Compose を使用）
cd ../..
docker compose up neo4j -d

# サンプルスクリプトを実行
cd examples/kg-minimal
pip install -r requirements.txt
python seed.py    # データのシード
python query.py   # クエリの実行
```

### ファイル構成

- `seed.py`: 記事で説明されているモデル定義（Cypher）を実行
- `query.py`: 記事で説明されているクエリ例を実行

## 3. ルールエンジン（ポリシーレイヤ）の最小構成

記事の「ハンズオン：OPA（Open Policy Agent）の最小例」に対応する例です。

### 実行方法

```bash
cd examples/policy-minimal

# OPA をインストール（macOS）
brew install opa

# または Docker を使用
docker run --rm -v $(pwd):/workspace openpolicyagent/opa:latest eval \
  -i input.json -d sla.rego "data.sla.priority"

# Python スクリプトで実行（OPA サーバーを使用）
python query.py
```

### ファイル構成

- `sla.rego`: 記事で説明されているポリシー定義
- `input.json`: 記事で説明されている入力例
- `query.py`: OPA サーバーを使用したクエリ例

## 4. 制約ソルバ（最適化レイヤ）の最小構成

記事の「ハンズオン：OR-Tools の最小例」に対応する例です。

### 実行方法

```bash
cd examples/optimization-minimal
pip install -r requirements.txt
python solve.py
```

### ファイル構成

- `solve.py`: 記事で説明されている OR-Tools の最小例

## 注意事項

これらの例は、記事のハンズオンセクションで説明されている最小構成を実際に実行できるようにしたものです。

実際の本番環境では、各レイヤは API サービスとして実装されています（`../sql-layer`, `../kg-layer`, `../policy-layer`, `../optimization-layer` を参照）。

