# Mobile Demo - 開発支援Webアプリ SDD（Software Design Document）

## 1. アーキテクチャ概要

### 1.1 システム構成
```
┌─────────────────┐
│   Web Browser   │
│   (HTMX Client) │
└────────┬────────┘
         │ HTTP/HTMX
         │
┌────────▼─────────────────────────┐
│      FastAPI Application         │
│  ┌─────────────────────────────┐ │
│  │   API Layer (REST API)      │ │
│  └──────────┬──────────────────┘ │
│  ┌──────────▼──────────────────┐ │
│  │   Service Layer             │ │
│  └──────────┬──────────────────┘ │
│  ┌──────────▼──────────────────┐ │
│  │   Repository Layer          │ │
│  └──────────┬──────────────────┘ │
└─────────────┼─────────────────────┘
              │
┌─────────────▼─────────────┐
│   SQLite Database         │
│   (SQLModel ORM)          │
└───────────────────────────┘
```

### 1.2 ディレクトリ構造
```
mobile-demo/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPIアプリケーションエントリーポイント
│   ├── config.py               # 設定管理
│   ├── database.py             # データベース接続設定
│   │
│   ├── models/                 # SQLModelモデル
│   │   ├── __init__.py
│   │   ├── api_spec.py
│   │   ├── test_data.py
│   │   ├── mock_endpoint.py
│   │   └── log_entry.py
│   │
│   ├── schemas/                # Pydanticスキーマ（APIリクエスト/レスポンス）
│   │   ├── __init__.py
│   │   ├── api_spec.py
│   │   ├── test_data.py
│   │   ├── mock_endpoint.py
│   │   └── log_entry.py
│   │
│   ├── repositories/           # データアクセス層（DRY原則）
│   │   ├── __init__.py
│   │   ├── base.py            # ベースリポジトリ（共通CRUD操作）
│   │   ├── api_spec_repository.py
│   │   ├── test_data_repository.py
│   │   ├── mock_endpoint_repository.py
│   │   └── log_entry_repository.py
│   │
│   ├── services/              # ビジネスロジック層
│   │   ├── __init__.py
│   │   ├── api_spec_service.py
│   │   ├── test_data_service.py
│   │   ├── mock_service.py
│   │   └── log_service.py
│   │
│   ├── api/                   # APIエンドポイント
│   │   ├── __init__.py
│   │   ├── deps.py            # 依存性注入（DBセッションなど）
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── api_specs.py
│   │   │   ├── test_data.py
│   │   │   ├── mocks.py
│   │   │   └── logs.py
│   │   └── mock_router.py     # 動的モックエンドポイント
│   │
│   └── templates/             # HTMLテンプレート（Jinja2）
│       ├── base.html
│       ├── index.html
│       ├── specs/
│       │   ├── list.html
│       │   ├── detail.html
│       │   └── form.html
│       ├── test_data/
│       │   ├── list.html
│       │   ├── detail.html
│       │   └── form.html
│       ├── mocks/
│       │   ├── list.html
│       │   ├── detail.html
│       │   └── form.html
│       └── logs/
│           ├── list.html
│           └── detail.html
│
├── tests/                     # テストコード
│   ├── __init__.py
│   ├── test_api_specs.py
│   ├── test_test_data.py
│   ├── test_mocks.py
│   └── test_logs.py
│
├── requirements.txt           # Python依存関係
├── README.md                  # プロジェクト説明
├── SPEC.md                    # 仕様書
└── SDD.md                     # 本ドキュメント
```

## 2. データモデル設計

### 2.1 ベースモデル（共通フィールド）
```python
# app/models/base.py
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class TimestampMixin(SQLModel):
    """タイムスタンプの共通フィールド"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
```

### 2.2 API仕様モデル
```python
# app/models/api_spec.py
from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from .base import TimestampMixin

class ApiSpec(SQLModel, TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    version: str
    openapi_spec: Dict[str, Any]  # JSON形式
    description: Optional[str] = None
```

### 2.3 テストデータモデル
```python
# app/models/test_data.py
from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any, List
from .base import TimestampMixin

class TestData(SQLModel, TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category: str = Field(index=True)  # APIエンドポイント名など
    data: Dict[str, Any]  # JSON形式
    description: Optional[str] = None
    tags: Optional[str] = None  # カンマ区切り
```

### 2.4 モックエンドポイントモデル
```python
# app/models/mock_endpoint.py
from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from .base import TimestampMixin

class MockEndpoint(SQLModel, TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    path: str = Field(index=True)  # 例: "/api/v1/users/{id}"
    method: str = Field(index=True)  # GET, POST, PUT, DELETE
    status_code: int = Field(default=200)
    response_body: Dict[str, Any]  # JSON形式
    response_headers: Optional[Dict[str, str]] = None
    is_active: bool = Field(default=True, index=True)
    description: Optional[str] = None
```

### 2.5 ログエントリモデル
```python
# app/models/log_entry.py
from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class LogEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    level: str = Field(index=True)  # INFO, WARN, ERROR
    message: str
    source: Optional[str] = Field(default=None, index=True)
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```

## 3. レイヤー設計

### 3.1 Repository層（データアクセス層）

#### ベースリポジトリ（DRY原則）
```python
# app/repositories/base.py
from typing import Generic, TypeVar, Type, Optional, List
from sqlmodel import SQLModel, Session, select

ModelType = TypeVar("ModelType", bound=SQLModel)

class BaseRepository(Generic[ModelType]):
    """共通CRUD操作を提供するベースリポジトリ"""
    
    def __init__(self, model: Type[ModelType], session: Session):
        self.model = model
        self.session = session
    
    def get(self, id: int) -> Optional[ModelType]:
        return self.session.get(self.model, id)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        statement = select(self.model).offset(skip).limit(limit)
        return list(self.session.exec(statement))
    
    def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj
    
    def update(self, id: int, obj_data: dict) -> Optional[ModelType]:
        obj = self.get(id)
        if obj:
            for key, value in obj_data.items():
                setattr(obj, key, value)
            self.session.add(obj)
            self.session.commit()
            self.session.refresh(obj)
        return obj
    
    def delete(self, id: int) -> bool:
        obj = self.get(id)
        if obj:
            self.session.delete(obj)
            self.session.commit()
            return True
        return False
```

#### 各リポジトリの実装例
```python
# app/repositories/api_spec_repository.py
from typing import List, Optional
from sqlmodel import Session, select
from app.models.api_spec import ApiSpec
from app.repositories.base import BaseRepository

class ApiSpecRepository(BaseRepository[ApiSpec]):
    def __init__(self, session: Session):
        super().__init__(ApiSpec, session)
    
    def search(self, query: str) -> List[ApiSpec]:
        """名前または説明で検索"""
        statement = select(ApiSpec).where(
            ApiSpec.name.contains(query) | 
            ApiSpec.description.contains(query)
        )
        return list(self.session.exec(statement))
    
    def get_by_version(self, name: str, version: str) -> Optional[ApiSpec]:
        """名前とバージョンで取得"""
        statement = select(ApiSpec).where(
            ApiSpec.name == name,
            ApiSpec.version == version
        )
        return self.session.exec(statement).first()
```

### 3.2 Service層（ビジネスロジック層）

```python
# app/services/api_spec_service.py
from typing import List, Optional
from sqlmodel import Session
from app.models.api_spec import ApiSpec
from app.repositories.api_spec_repository import ApiSpecRepository
from app.schemas.api_spec import ApiSpecCreate, ApiSpecUpdate

class ApiSpecService:
    def __init__(self, session: Session):
        self.repository = ApiSpecRepository(session)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ApiSpec]:
        return self.repository.get_all(skip, limit)
    
    def get_by_id(self, id: int) -> Optional[ApiSpec]:
        return self.repository.get(id)
    
    def create(self, spec_data: ApiSpecCreate) -> ApiSpec:
        spec = ApiSpec(**spec_data.dict())
        return self.repository.create(spec)
    
    def update(self, id: int, spec_data: ApiSpecUpdate) -> Optional[ApiSpec]:
        return self.repository.update(id, spec_data.dict(exclude_unset=True))
    
    def delete(self, id: int) -> bool:
        return self.repository.delete(id)
    
    def search(self, query: str) -> List[ApiSpec]:
        return self.repository.search(query)
```

### 3.3 API層（エンドポイント）

```python
# app/api/routes/api_specs.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
from typing import List
from app.api.deps import get_session
from app.services.api_spec_service import ApiSpecService
from app.schemas.api_spec import ApiSpecRead, ApiSpecCreate, ApiSpecUpdate

router = APIRouter(prefix="/api/specs", tags=["api-specs"])

@router.get("", response_model=List[ApiSpecRead])
def get_specs(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    service = ApiSpecService(session)
    return service.get_all(skip, limit)

@router.get("/{id}", response_model=ApiSpecRead)
def get_spec(id: int, session: Session = Depends(get_session)):
    service = ApiSpecService(session)
    spec = service.get_by_id(id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    return spec

@router.post("", response_model=ApiSpecRead)
def create_spec(spec_data: ApiSpecCreate, session: Session = Depends(get_session)):
    service = ApiSpecService(session)
    return service.create(spec_data)

@router.put("/{id}", response_model=ApiSpecRead)
def update_spec(
    id: int,
    spec_data: ApiSpecUpdate,
    session: Session = Depends(get_session)
):
    service = ApiSpecService(session)
    spec = service.update(id, spec_data)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    return spec

@router.delete("/{id}")
def delete_spec(id: int, session: Session = Depends(get_session)):
    service = ApiSpecService(session)
    if not service.delete(id):
        raise HTTPException(status_code=404, detail="Spec not found")
    return {"message": "Spec deleted"}

@router.get("/search", response_model=List[ApiSpecRead])
def search_specs(q: str, session: Session = Depends(get_session)):
    service = ApiSpecService(session)
    return service.search(q)
```

### 3.4 HTMXルート（HTMLレンダリング）

```python
# app/api/routes/api_specs.py（続き）
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

@router.get("/ui", response_class=HTMLResponse)
def list_specs_ui(request: Request, session: Session = Depends(get_session)):
    service = ApiSpecService(session)
    specs = service.get_all()
    return templates.TemplateResponse(
        "specs/list.html",
        {"request": request, "specs": specs}
    )

@router.post("/ui", response_class=HTMLResponse)
def create_spec_ui(
    request: Request,
    spec_data: ApiSpecCreate,
    session: Session = Depends(get_session)
):
    service = ApiSpecService(session)
    spec = service.create(spec_data)
    # HTMX用のレスポンス（部分更新）
    return templates.TemplateResponse(
        "specs/_spec_item.html",
        {"request": request, "spec": spec}
    )
```

## 4. モックサーバー設計

### 4.1 動的ルーティング
```python
# app/api/mock_router.py
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session
from app.api.deps import get_session
from app.repositories.mock_endpoint_repository import MockEndpointRepository
import re

router = APIRouter()

@router.api_route("/mock/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def mock_endpoint(
    path: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """動的にモックエンドポイントを処理"""
    method = request.method
    repository = MockEndpointRepository(session)
    
    # パスパターンマッチング
    active_mocks = repository.get_active_by_method(method)
    
    for mock in active_mocks:
        if match_path(mock.path, path):
            return JSONResponse(
                content=mock.response_body,
                status_code=mock.status_code,
                headers=mock.response_headers or {}
            )
    
    raise HTTPException(status_code=404, detail="Mock endpoint not found")

def match_path(pattern: str, path: str) -> bool:
    """パスパターンと実際のパスをマッチング（{id}などのパラメータ対応）"""
    # 例: "/api/v1/users/{id}" と "/api/v1/users/123"
    pattern_regex = re.sub(r'\{[^}]+\}', r'[^/]+', pattern)
    pattern_regex = f"^{pattern_regex}$"
    return bool(re.match(pattern_regex, path))
```

## 5. 設定管理

### 5.1 設定ファイル
```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Mobile Demo"
    database_url: str = "sqlite:///./mobile_demo.db"
    debug: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 5.2 データベース設定
```python
# app/database.py
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

engine = create_engine(settings.database_url, echo=settings.debug)

def init_db():
    """データベース初期化"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """セッション取得（依存性注入用）"""
    with Session(engine) as session:
        yield session
```

## 6. エラーハンドリング

### 6.1 カスタム例外
```python
# app/exceptions.py
from fastapi import HTTPException

class NotFoundError(HTTPException):
    def __init__(self, resource: str, id: int):
        super().__init__(status_code=404, detail=f"{resource} with id {id} not found")

class ValidationError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=400, detail=message)
```

### 6.2 グローバルエラーハンドラー
```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.exceptions import NotFoundError, ValidationError

app = FastAPI()

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
```

## 7. HTMX統合設計

### 7.1 ベーステンプレート
```html
<!-- app/templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Mobile Demo{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        /* 基本的なスタイル */
    </style>
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/specs/ui">API Specs</a>
        <a href="/test-data/ui">Test Data</a>
        <a href="/mocks/ui">Mocks</a>
        <a href="/logs/ui">Logs</a>
    </nav>
    
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

### 7.2 HTMX使用例
```html
<!-- app/templates/specs/list.html -->
{% extends "base.html" %}

{% block content %}
<h1>API Specs</h1>

<!-- HTMXで動的に追加 -->
<div id="spec-list" hx-get="/api/specs" hx-trigger="load">
    Loading...
</div>

<!-- フォーム（HTMXで送信） -->
<form hx-post="/api/specs/ui" hx-target="#spec-list" hx-swap="beforeend">
    <input name="name" placeholder="Spec Name" required>
    <input name="version" placeholder="Version" required>
    <textarea name="openapi_spec" placeholder="OpenAPI Spec (JSON)"></textarea>
    <button type="submit">Add</button>
</form>
{% endblock %}
```

## 8. テスト戦略

### 8.1 ユニットテスト
- Repository層のテスト
- Service層のテスト
- モデルのバリデーションテスト

### 8.2 統合テスト
- APIエンドポイントのテスト
- データベース操作のテスト
- HTMXルートのテスト

### 8.3 テストツール
- pytest
- pytest-asyncio（FastAPI用）
- httpx（テストクライアント）

## 9. デプロイメント

### 9.1 開発環境
```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# データベース初期化
python -m app.database init_db

# アプリケーション起動
uvicorn app.main:app --reload
```

### 9.2 本番環境
- Dockerコンテナ化を検討
- PostgreSQLへの移行
- 環境変数による設定管理

## 10. パフォーマンス最適化

### 10.1 データベース
- インデックスの適切な設定
- ページネーションの実装
- クエリの最適化

### 10.2 キャッシング
- よく使われるデータのキャッシュ（将来的に）
- Redisの導入検討

## 11. セキュリティ考慮事項

### 11.1 入力検証
- Pydanticによる自動バリデーション
- SQLインジェクション対策（SQLModel使用）

### 11.2 XSS対策
- HTMXの自動エスケープ
- Jinja2の自動エスケープ

### 11.3 認証・認可（将来）
- JWT認証の実装
- ロールベースアクセス制御
