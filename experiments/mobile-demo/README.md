# Mobile Demo - 開発支援Webアプリ

携帯電話会社の開発チームをサポートするための開発支援Webアプリケーション（MVP）。

## 概要

開発チームが共通で抱えている課題を解決するためのWebアプリケーションです。

### 主な機能

1. **API仕様管理** - OpenAPI仕様の管理・共有
2. **テストデータ管理** - JSON形式のテストデータの管理・再利用
3. **モックサーバー** - 開発用のモックエンドポイント提供
4. **ログビューアー** - 開発ログの閲覧・検索

## 技術スタック

- **バックエンド**: FastAPI
- **フロントエンド**: HTMX
- **データベース**: SQLModel (SQLite for MVP)
- **原則**: DRY原則に従った設計

## ドキュメント

- [SPEC.md](./SPEC.md) - 機能仕様書
- [SDD.md](./SDD.md) - ソフトウェア設計書

## プロジェクト構造

```
mobile-demo/
├── app/                    # アプリケーションコード
│   ├── models/            # SQLModelモデル
│   ├── schemas/           # Pydanticスキーマ
│   ├── repositories/      # データアクセス層
│   ├── services/          # ビジネスロジック層
│   ├── api/               # APIエンドポイント
│   └── templates/         # HTMLテンプレート
├── tests/                 # テストコード
├── requirements.txt       # Python依存関係
├── SPEC.md                # 仕様書
├── SDD.md                 # 設計書
└── README.md              # 本ファイル
```

## セットアップ（予定）

```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# データベース初期化
python -m app.database init_db

# アプリケーション起動
uvicorn app.main:app --reload
```

## 開発フェーズ

1. ✅ スペック作成
2. ✅ SDD作成
3. ⏳ 実装（これから）

## ライセンス

内部プロジェクト
