# Phase 0: 项目脚手架搭建 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从现有建筑 ERP 复制精简，搭建招投标管理平台的前后端骨架，跑通登录流程。

**Architecture:** 前后端分离。后端 FastAPI + SQLAlchemy（SQLite 开发），前端 React 18 + TypeScript + Ant Design 5 + Vite。从建筑 ERP（`/Users/wangyunchen/agents/建筑公司`）复制基础设施代码，去掉所有业务模块和多租户，只保留认证流程。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic 2.x, JWT (python-jose), React 18, TypeScript, Vite, Ant Design 5, Zustand, Axios

**Source ERP:** `/Users/wangyunchen/agents/建筑公司`（前端 `construction-erp-frontend/`，后端 `construction-erp-backend/`）

---

## File Map

### Backend (`backend/`)

| File | Responsibility |
|---|---|
| `app/__init__.py` | Package init |
| `app/main.py` | FastAPI 入口，注册路由+中间件+异常处理+初始化 |
| `app/config.py` | pydantic-settings 配置管理 |
| `app/database.py` | SQLAlchemy async engine + session |
| `app/models/__init__.py` | Package init |
| `app/models/base.py` | ORM 基类（AuditMixin，无 TenantMixin） |
| `app/models/system.py` | SysUser 模型 |
| `app/schemas/__init__.py` | Package init |
| `app/schemas/auth.py` | 登录/刷新/改密 Pydantic Schema |
| `app/services/__init__.py` | Package init |
| `app/services/auth_service.py` | 认证业务逻辑 |
| `app/routers/__init__.py` | Package init |
| `app/routers/auth.py` | /api/v1/auth/* 路由 |
| `app/common/__init__.py` | Package init |
| `app/common/security.py` | JWT + bcrypt（无 tenant_id） |
| `app/common/deps.py` | FastAPI 依赖注入（无多租户） |
| `app/common/response.py` | 统一响应格式 |
| `app/common/exceptions.py` | 自定义异常类 |
| `app/common/pagination.py` | 分页工具 |
| `requirements.txt` | Python 依赖 |
| `.env.example` | 环境变量模板 |
| `data/.gitkeep` | SQLite 数据目录 |

### Frontend (`frontend/`)

| File | Responsibility |
|---|---|
| `package.json` | 依赖和脚本 |
| `tsconfig.json` | TypeScript 配置 |
| `tsconfig.node.json` | Vite node 配置 |
| `vite.config.ts` | Vite 构建+代理配置 |
| `index.html` | HTML 入口 |
| `src/main.tsx` | React 挂载入口 |
| `src/app.tsx` | App 根组件（主题+Provider） |
| `src/routes.tsx` | 路由配置 |
| `src/global.tsx` | 全局副作用 |
| `src/access.ts` | 权限映射框架 |
| `src/vite-env.d.ts` | Vite 类型声明 |
| `src/styles/global.css` | Teal 设计系统 CSS 变量 |
| `src/layouts/BasicLayout.tsx` | 主布局（侧边栏+顶栏） |
| `src/layouts/BlankLayout.tsx` | 空白布局（登录页） |
| `src/pages/Login/index.tsx` | 登录页 |
| `src/pages/Dashboard/index.tsx` | 仪表盘占位页 |
| `src/stores/useAuthStore.ts` | 认证状态管理 |
| `src/services/auth.ts` | 认证 API 调用 |
| `src/utils/auth.ts` | Token 存取工具 |
| `src/utils/request.ts` | Axios 实例封装 |
| `src/constants/index.ts` | 全局常量 |
| `src/constants/api.ts` | API 路径常量 |
| `src/types/api.ts` | 通用类型定义 |

---

## Task 1: 后端基础设施

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/data/.gitkeep`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Create requirements.txt**

```
# FastAPI & ASGI
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.18

# Database
sqlalchemy[asyncio]==2.0.36
aiosqlite==0.20.0
alembic==1.14.0

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.2.1

# Validation & Serialization
pydantic==2.10.3
pydantic-settings==2.7.0
email-validator==2.2.0

# Utilities
python-dotenv==1.0.1
httpx==0.28.1
orjson==3.10.12

# Testing
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create .env.example**

```
APP_ENV=development
APP_DEBUG=true
DB_TYPE=sqlite
JWT_SECRET_KEY=change-this-in-production
CORS_ORIGINS=["http://localhost:5180"]
```

- [ ] **Step 3: Create data/.gitkeep and app/__init__.py**

```bash
mkdir -p backend/data && touch backend/data/.gitkeep
mkdir -p backend/app && touch backend/app/__init__.py
```

- [ ] **Step 4: Create config.py**

Write `backend/app/config.py`:

```python
"""
配置管理模块
"""

import json
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 应用配置
    APP_NAME: str = "bid-system"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8002

    # 数据库配置
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root123456"
    DB_NAME: str = "bid_system"
    DB_TYPE: str = "sqlite"

    # JWT 配置
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS 配置
    CORS_ORIGINS: str = '["http://localhost:5180"]'

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bid.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            return f"sqlite+aiosqlite:///{db_path}"
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bid.db")
            return f"sqlite:///{db_path}"
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:5180"]


settings = Settings()
```

- [ ] **Step 5: Create database.py**

Write `backend/app/database.py`:

```python
"""
数据库连接管理模块
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

_engine_kwargs = {
    "echo": settings.APP_DEBUG,
}
if settings.DB_TYPE != "sqlite":
    _engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db_session():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    await engine.dispose()
```

- [ ] **Step 6: Install dependencies and verify import**

```bash
cd backend && pip install -r requirements.txt
python -c "from app.config import settings; print(settings.APP_NAME)"
```

Expected: `bid-system`

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/data/.gitkeep backend/app/__init__.py backend/app/config.py backend/app/database.py
git commit -m "feat: add backend infrastructure (config, database, dependencies)"
```

---

## Task 2: 后端 common 模块

**Files:**
- Create: `backend/app/common/__init__.py`
- Create: `backend/app/common/security.py`
- Create: `backend/app/common/response.py`
- Create: `backend/app/common/exceptions.py`
- Create: `backend/app/common/pagination.py`
- Create: `backend/app/common/deps.py`

- [ ] **Step 1: Create common/__init__.py**

```bash
mkdir -p backend/app/common && touch backend/app/common/__init__.py
```

- [ ] **Step 2: Create security.py（无 tenant_id）**

Write `backend/app/common/security.py`:

```python
"""
安全模块 - JWT Token 生成/验证、密码哈希/验证
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload
    return None


def decode_refresh_token(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if payload and payload.get("type") == "refresh":
        return payload
    return None
```

- [ ] **Step 3: Create response.py**

Write `backend/app/common/response.py`:

```python
"""
统一响应格式
"""

import time
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    code: int = Field(default=200)
    message: str = Field(default="success")
    data: Optional[Any] = Field(default=None)
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class PageData(BaseModel):
    items: list = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    total_pages: int = Field(default=0)


def success(data: Any = None, message: str = "success") -> dict:
    return ResponseModel(code=200, message=message, data=data).model_dump()


def fail(message: str = "操作失败", code: int = 400, data: Any = None) -> dict:
    return ResponseModel(code=code, message=message, data=data).model_dump()


def page_response(items: list, total: int, page: int, page_size: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    page_data = PageData(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)
    return success(data=page_data.model_dump())
```

- [ ] **Step 4: Create exceptions.py（去掉 ApprovalException）**

Write `backend/app/common/exceptions.py`:

```python
"""
自定义异常类
"""


class BusinessException(Exception):
    def __init__(self, message: str = "业务处理异常", code: int = 400):
        self.code = code
        self.message = message
        super().__init__(self.message)


class NotFoundException(Exception):
    def __init__(self, message: str = "请求的资源不存在"):
        self.message = message
        super().__init__(self.message)


class ForbiddenException(Exception):
    def __init__(self, message: str = "权限不足，无法执行此操作"):
        self.message = message
        super().__init__(self.message)


class UnauthorizedException(Exception):
    def __init__(self, message: str = "未登录或登录已过期"):
        self.message = message
        super().__init__(self.message)


class ValidationException(BusinessException):
    def __init__(self, message: str = "参数校验失败", errors: list = None):
        super().__init__(message=message, code=422)
        self.errors = errors or []


class DuplicateException(BusinessException):
    def __init__(self, message: str = "数据已存在"):
        super().__init__(message=message, code=409)
```

- [ ] **Step 5: Create pagination.py**

Write `backend/app/common/pagination.py`:

```python
"""
分页工具
"""

from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = Field(default=None)
    sort_order: Optional[str] = Field(default="desc")


def get_pagination_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: Optional[str] = Query(default=None),
    sort_order: Optional[str] = Query(default="desc"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)


async def paginate(
    session: AsyncSession,
    query: Select,
    params: PaginationParams,
    sort_column=None,
) -> dict:
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    if sort_column is not None:
        if params.sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

    offset = (params.page - 1) * params.page_size
    query = query.offset(offset).limit(params.page_size)

    result = await session.execute(query)
    items = result.scalars().all()

    total_pages = (total + params.page_size - 1) // params.page_size if params.page_size > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "total_pages": total_pages,
    }
```

- [ ] **Step 6: Create deps.py（无多租户）**

Write `backend/app/common/deps.py`:

```python
"""
依赖注入模块
"""

from typing import Optional

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.common.exceptions import UnauthorizedException
from app.common.security import decode_access_token


async def get_db(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    return session


async def get_current_user_id(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> int:
    if not authorization:
        raise UnauthorizedException("缺少认证信息")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException("无效的认证格式")

    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException("Token 无效或已过期")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException("Token 中缺少用户信息")

    return int(user_id)


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from app.models.system import SysUser

    result = await db.execute(
        select(SysUser).where(
            SysUser.id == user_id,
            SysUser.is_deleted == 0,
            SysUser.status == 1,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException("用户不存在或已被禁用")

    return user
```

- [ ] **Step 7: Verify imports**

```bash
cd backend && python -c "from app.common.security import hash_password; print(hash_password('test')[:10])"
```

Expected: 输出 bcrypt hash 前缀 `$2b$12$...`

- [ ] **Step 8: Commit**

```bash
git add backend/app/common/
git commit -m "feat: add backend common modules (security, response, exceptions, pagination, deps)"
```

---

## Task 3: 后端 Model + Schema + Service + Router

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/system.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`

- [ ] **Step 1: Create package inits**

```bash
mkdir -p backend/app/models backend/app/schemas backend/app/services backend/app/routers backend/app/repositories
touch backend/app/models/__init__.py backend/app/schemas/__init__.py backend/app/services/__init__.py backend/app/routers/__init__.py backend/app/repositories/__init__.py
```

- [ ] **Step 2: Create models/base.py（无 TenantMixin）**

Write `backend/app/models/base.py`:

```python
"""
ORM 模型基类
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base

_pk_type = Integer if settings.DB_TYPE == "sqlite" else BigInteger


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(),
    )
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int] = mapped_column(BigInteger, nullable=True)
    is_deleted: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0",
    )


class BaseModel(Base, AuditMixin):
    __abstract__ = True

    id: Mapped[int] = mapped_column(_pk_type, primary_key=True, autoincrement=True)
```

- [ ] **Step 3: Create models/system.py**

Write `backend/app/models/system.py`:

```python
"""
系统模型 - 用户表
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import SmallInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SysUser(BaseModel):
    __tablename__ = "sys_user"

    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="USER", server_default="USER")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 4: Create schemas/auth.py**

Write `backend/app/schemas/auth.py`:

```python
"""
认证相关 Schema
"""

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(...)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class UserInfo(BaseModel):
    id: int
    username: str
    real_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    role: str = "USER"
    permissions: list[str] = []
```

- [ ] **Step 5: Create services/auth_service.py**

Write `backend/app/services/auth_service.py`:

```python
"""
认证服务
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import BusinessException, UnauthorizedException
from app.common.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.models.system import SysUser


class AuthService:

    async def login(self, db: AsyncSession, username: str, password: str) -> dict:
        result = await db.execute(
            select(SysUser).where(SysUser.username == username, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise BusinessException("用户名或密码错误")
        if user.status != 1:
            raise BusinessException("账号已被禁用")
        if not verify_password(password, user.password_hash):
            raise BusinessException("用户名或密码错误")

        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def refresh_token(self, db: AsyncSession, refresh_token: str) -> dict:
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise UnauthorizedException("Refresh Token 无效或已过期")

        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("Token 中缺少用户信息")

        result = await db.execute(
            select(SysUser).where(SysUser.id == int(user_id), SysUser.is_deleted == 0, SysUser.status == 1)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UnauthorizedException("用户不存在或已被禁用")

        token_data = {"sub": str(user.id)}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "token_type": "Bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def get_current_user_info(self, db: AsyncSession, user_id: int) -> dict:
        result = await db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UnauthorizedException("用户不存在")

        is_super_admin = user.role == "SUPER_ADMIN"
        permissions = ["*"] if is_super_admin else []

        return {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "phone": user.phone,
            "email": user.email,
            "avatar": user.avatar,
            "role": user.role,
            "permissions": permissions,
        }

    async def change_password(self, db: AsyncSession, user_id: int, old_password: str, new_password: str) -> bool:
        result = await db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException("用户不存在")
        if not verify_password(old_password, user.password_hash):
            raise BusinessException("旧密码不正确")

        user.password_hash = hash_password(new_password)
        await db.flush()
        return True


auth_service = AuthService()
```

- [ ] **Step 6: Create routers/auth.py**

Write `backend/app/routers/auth.py`:

```python
"""
认证路由 /api/v1/auth/*
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id
from app.common.response import success
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshTokenRequest
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/login", summary="用户登录")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    data = await auth_service.login(db, request.username, request.password)
    return success(data=data)


@router.post("/logout", summary="退出登录")
async def logout(user_id: int = Depends(get_current_user_id)):
    return success(message="退出成功")


@router.post("/refresh", summary="刷新 Token")
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    data = await auth_service.refresh_token(db, request.refresh_token)
    return success(data=data)


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    data = await auth_service.get_current_user_info(db, user_id)
    return success(data=data)


@router.put("/password", summary="修改密码")
async def change_password(
    request: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.change_password(db, user_id, request.old_password, request.new_password)
    return success(message="密码修改成功")
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/ backend/app/schemas/ backend/app/services/ backend/app/routers/ backend/app/repositories/
git commit -m "feat: add auth model, schema, service and router"
```

---

## Task 4: 后端 main.py + 启动验证

**Files:**
- Create: `backend/app/main.py`

- [ ] **Step 1: Create main.py**

Write `backend/app/main.py`:

```python
"""
招投标管理平台 - FastAPI 应用入口
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import close_db, init_db, async_session_factory
from app.common.exceptions import (
    BusinessException,
    NotFoundException,
    ForbiddenException,
    UnauthorizedException,
)
from app.common.response import ResponseModel

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动中...")
    await init_db()
    await _init_base_data()
    yield
    await close_db()
    logger.info("应用已关闭")


app = FastAPI(
    title="招投标管理平台",
    description="招投标管理平台后端 API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(status_code=200, content=ResponseModel(code=exc.code, message=exc.message, data=None).model_dump())


@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(status_code=404, content=ResponseModel(code=404, message=exc.message, data=None).model_dump())


@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(status_code=403, content=ResponseModel(code=403, message=exc.message, data=None).model_dump())


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(status_code=401, content=ResponseModel(code=401, message=exc.message, data=None).model_dump())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content=ResponseModel(code=500, message="服务器内部错误", data=None).model_dump())


# 注册路由
from app.routers import auth

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证管理"])


@app.get("/api/health", tags=["健康检查"])
async def health_check():
    return ResponseModel(code=200, message="ok", data={"status": "healthy"})


async def _init_base_data():
    from sqlalchemy import select
    from app.models.system import SysUser
    from app.common.security import hash_password

    async with async_session_factory() as session:
        result = await session.execute(
            select(SysUser).where(SysUser.username == "admin")
        )
        if not result.scalar_one_or_none():
            admin = SysUser(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="系统管理员",
                phone="13800000000",
                role="SUPER_ADMIN",
                status=1,
            )
            session.add(admin)
            await session.commit()
            logger.info("默认管理员 admin/admin123 已创建")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.APP_DEBUG)
```

- [ ] **Step 2: Start backend and test**

```bash
cd backend && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Expected: 启动成功，日志显示"默认管理员已创建"

- [ ] **Step 3: Test health check**

```bash
curl http://localhost:8002/api/health
```

Expected: `{"code":200,"message":"ok","data":{"status":"healthy"},...}`

- [ ] **Step 4: Test login**

```bash
curl -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}'
```

Expected: `{"code":200,"data":{"access_token":"eyJ...","refresh_token":"eyJ...","token_type":"Bearer","expires_in":7200},...}`

- [ ] **Step 5: Test /me with token**

```bash
TOKEN=$(curl -s -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/auth/me
```

Expected: `{"code":200,"data":{"id":1,"username":"admin","real_name":"系统管理员","role":"SUPER_ADMIN",...},...}`

- [ ] **Step 6: Stop backend, commit**

```bash
git add backend/app/main.py
git commit -m "feat: add FastAPI main entry with auth routes and admin initialization"
```

---

## Task 5: 前端基础设施

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/vite-env.d.ts`

- [ ] **Step 1: Create package.json**

Write `frontend/package.json`:

```json
{
  "name": "bid-system-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "antd": "^5.12.0",
    "@ant-design/icons": "^5.2.6",
    "zustand": "^4.4.7",
    "axios": "^1.6.2",
    "dayjs": "^1.11.10",
    "classnames": "^2.3.2",
    "nprogress": "^0.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.42",
    "@types/react-dom": "^18.2.17",
    "@types/nprogress": "^0.2.3",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.8"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

Write `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": "./",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Create tsconfig.node.json**

Write `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create vite.config.ts**

Write `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5180,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          antd: ['antd', '@ant-design/icons'],
        },
      },
    },
  },
});
```

- [ ] **Step 5: Create index.html**

Write `frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="招投标管理平台" />
    <link rel="icon" type="image/x-icon" href="/favicon.ico" />
    <title>招投标管理平台</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create vite-env.d.ts**

Write `frontend/src/vite-env.d.ts`:

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 7: Install dependencies**

```bash
cd frontend && npm install
```

Expected: 安装成功，无 error

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/src/vite-env.d.ts frontend/package-lock.json
git commit -m "feat: add frontend build infrastructure (Vite, TypeScript, Ant Design)"
```

---

## Task 6: 前端公共模块（类型、常量、工具）

**Files:**
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/constants/index.ts`
- Create: `frontend/src/constants/api.ts`
- Create: `frontend/src/utils/auth.ts`
- Create: `frontend/src/utils/request.ts`
- Create: `frontend/src/global.tsx`

- [ ] **Step 1: Create types/api.ts**

Write `frontend/src/types/api.ts`:

```typescript
/** 统一 API 响应 */
interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  timestamp: number;
}

/** 分页响应 */
interface PaginatedData<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** 当前用户 */
interface CurrentUser {
  id: number;
  username: string;
  real_name: string;
  phone?: string;
  email?: string;
  avatar?: string;
  role: string;
  permissions: string[];
}

/** 登录参数 */
interface LoginParams {
  username: string;
  password: string;
}

/** 登录结果 */
interface LoginResult {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
```

- [ ] **Step 2: Create constants/index.ts**

Write `frontend/src/constants/index.ts`:

```typescript
export const SYSTEM_NAME = '招投标管理平台';
export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];
export const ACCESS_TOKEN_KEY = 'bid_system_access_token';
export const REFRESH_TOKEN_KEY = 'bid_system_refresh_token';
export const DATE_FORMAT = 'YYYY-MM-DD';
export const DATETIME_FORMAT = 'YYYY-MM-DD HH:mm:ss';
```

- [ ] **Step 3: Create constants/api.ts**

Write `frontend/src/constants/api.ts`:

```typescript
const API_PREFIX = '/api/v1';

export const AUTH_API = {
  LOGIN: `${API_PREFIX}/auth/login`,
  LOGOUT: `${API_PREFIX}/auth/logout`,
  REFRESH: `${API_PREFIX}/auth/refresh`,
  ME: `${API_PREFIX}/auth/me`,
  CHANGE_PASSWORD: `${API_PREFIX}/auth/password`,
} as const;
```

- [ ] **Step 4: Create utils/auth.ts**

Write `frontend/src/utils/auth.ts`:

```typescript
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '@/constants';

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function saveTokens(accessToken: string, refreshToken: string): void {
  setAccessToken(accessToken);
  setRefreshToken(refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}
```

- [ ] **Step 5: Create utils/request.ts**

Write `frontend/src/utils/request.ts`:

```typescript
import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import { message } from 'antd';
import { getAccessToken, clearTokens } from './auth';

const request = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

request.interceptors.response.use(
  (response) => {
    const { data } = response;
    if (data.code !== undefined && data.code !== 200) {
      message.error(data.message || '请求失败');
      return Promise.reject(new Error(data.message || '请求失败'));
    }
    return data;
  },
  (error: AxiosError<ApiResponse>) => {
    const { response } = error;
    if (response) {
      switch (response.status) {
        case 401:
          message.error('登录已过期，请重新登录');
          clearTokens();
          window.location.href = '/login';
          break;
        case 403:
          message.error('没有权限访问该资源');
          break;
        case 404:
          message.error('请求的资源不存在');
          break;
        default:
          message.error(response.data?.message || `请求失败 (${response.status})`);
      }
    } else if (error.message.includes('timeout')) {
      message.error('请求超时，请稍后重试');
    } else if (error.message.includes('Network Error')) {
      message.error('网络异常，请检查网络连接');
    }
    return Promise.reject(error);
  },
);

export function get<T = unknown>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return request.get(url, { params, ...config });
}

export function post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return request.post(url, data, config);
}

export function put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return request.put(url, data, config);
}

export function del<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  return request.delete(url, config);
}

export default request;
```

- [ ] **Step 6: Create global.tsx**

Write `frontend/src/global.tsx`:

```typescript
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled Promise Rejection:', event.reason);
});
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/ frontend/src/constants/ frontend/src/utils/ frontend/src/global.tsx
git commit -m "feat: add frontend common modules (types, constants, utils, request)"
```

---

## Task 7: 前端 Store + Service + 样式

**Files:**
- Create: `frontend/src/stores/useAuthStore.ts`
- Create: `frontend/src/services/auth.ts`
- Create: `frontend/src/styles/global.css`
- Create: `frontend/src/access.ts`

- [ ] **Step 1: Create services/auth.ts**

Write `frontend/src/services/auth.ts`:

```typescript
import { get, post, put } from '@/utils/request';
import { AUTH_API } from '@/constants/api';

export function login(params: LoginParams) {
  return post<LoginResult>(AUTH_API.LOGIN, params);
}

export function logout() {
  return post(AUTH_API.LOGOUT);
}

export function refreshToken(refresh_token: string) {
  return post<LoginResult>(AUTH_API.REFRESH, { refresh_token });
}

export function getCurrentUser() {
  return get<CurrentUser>(AUTH_API.ME);
}

export function changePassword(data: { old_password: string; new_password: string }) {
  return put(AUTH_API.CHANGE_PASSWORD, data);
}
```

- [ ] **Step 2: Create stores/useAuthStore.ts（无租户、无注册）**

Write `frontend/src/stores/useAuthStore.ts`:

```typescript
import { create } from 'zustand';
import { saveTokens, clearTokens, isAuthenticated } from '@/utils/auth';
import { login as loginApi, logout as logoutApi, getCurrentUser } from '@/services/auth';

interface AuthState {
  currentUser: CurrentUser | null;
  isLoggedIn: boolean;
  permissions: string[];
  loading: boolean;
  login: (params: LoginParams) => Promise<void>;
  logout: () => Promise<void>;
  fetchCurrentUser: () => Promise<CurrentUser | null>;
  reset: () => void;
}

const useAuthStore = create<AuthState>((set) => ({
  currentUser: null,
  isLoggedIn: isAuthenticated(),
  permissions: [],
  loading: false,

  login: async (params: LoginParams) => {
    set({ loading: true });
    try {
      const res = await loginApi(params);
      const { access_token, refresh_token } = res.data;
      saveTokens(access_token, refresh_token);
      set({ isLoggedIn: true });

      const userRes = await getCurrentUser();
      set({
        currentUser: userRes.data,
        permissions: userRes.data.permissions || [],
      });
    } finally {
      set({ loading: false });
    }
  },

  logout: async () => {
    try {
      await logoutApi();
    } finally {
      clearTokens();
      set({ currentUser: null, isLoggedIn: false, permissions: [] });
    }
  },

  fetchCurrentUser: async () => {
    if (!isAuthenticated()) return null;
    set({ loading: true });
    try {
      const res = await getCurrentUser();
      set({
        currentUser: res.data,
        permissions: res.data.permissions || [],
        isLoggedIn: true,
      });
      return res.data;
    } catch {
      clearTokens();
      set({ currentUser: null, isLoggedIn: false, permissions: [] });
      return null;
    } finally {
      set({ loading: false });
    }
  },

  reset: () => {
    clearTokens();
    set({ currentUser: null, isLoggedIn: false, permissions: [], loading: false });
  },
}));

export default useAuthStore;
```

- [ ] **Step 3: Create access.ts**

Write `frontend/src/access.ts`:

```typescript
export function getAccessMap(currentUser: CurrentUser | null): Record<string, boolean> {
  if (!currentUser) return {};

  const isSuperAdmin = currentUser.role === 'SUPER_ADMIN';

  return {
    isSuperAdmin,
    canAccessSystem: isSuperAdmin,
    canAccessDashboard: true,
  };
}
```

- [ ] **Step 4: Create styles/global.css（Teal 主题）**

Write `frontend/src/styles/global.css`:

```css
/* Bid System - Teal Design System */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  /* Primary Colors - Teal */
  --color-primary: #0d9488;
  --color-primary-hover: #14b8a6;
  --color-primary-active: #0f766e;
  --color-primary-gradient: linear-gradient(135deg, #0d9488, #14b8a6);

  /* Backgrounds */
  --color-bg-dark: #042f2e;
  --color-bg-page: #f1f5f9;
  --color-bg-card: #ffffff;
  --color-bg-sidebar: #042f2e;

  /* Text */
  --color-text-primary: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #94a3b8;
  --color-text-white: #ffffff;

  /* Border */
  --color-border: #e2e8f0;

  /* Status */
  --color-success: #10B981;
  --color-warning: #D97706;
  --color-error: #EF4444;
  --color-info: #0d9488;

  /* Radius */
  --radius-card: 14px;
  --radius-btn: 8px;
  --radius-input: 8px;

  /* Shadow */
  --shadow-card: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-card-hover: 0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.04);
  --shadow-btn-primary: 0 4px 14px rgba(13, 148, 136, 0.35);

  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;

  /* Layout */
  --sidebar-width: 240px;
  --header-height: 64px;

  /* Font */
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Global Reset */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font-family);
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* Ant Design Overrides */
.ant-card {
  border-radius: var(--radius-card) !important;
  box-shadow: var(--shadow-card) !important;
  border: 1px solid var(--color-border) !important;
}

.ant-card:hover {
  box-shadow: var(--shadow-card-hover) !important;
}

.ant-btn-primary {
  box-shadow: var(--shadow-btn-primary) !important;
}

.ant-btn-primary:hover {
  box-shadow: 0 6px 20px rgba(13, 148, 136, 0.45) !important;
}

.ant-table-wrapper .ant-table-thead > tr > th {
  background: transparent !important;
  color: var(--color-text-muted) !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  border-bottom: 2px solid var(--color-border) !important;
}

.ant-table-wrapper .ant-table-tbody > tr:hover > td {
  background: rgba(13, 148, 136, 0.04) !important;
}

.ant-menu-dark .ant-menu-item-selected {
  background: rgba(13, 148, 136, 0.15) !important;
  border-left: 3px solid #0d9488;
}

.ant-tag {
  border-radius: 6px !important;
  font-weight: 500 !important;
}

.ant-modal .ant-modal-content {
  border-radius: var(--radius-card) !important;
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/ frontend/src/services/ frontend/src/styles/ frontend/src/access.ts
git commit -m "feat: add auth store, auth service, access control and Teal design system"
```

---

## Task 8: 前端页面和布局

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app.tsx`
- Create: `frontend/src/routes.tsx`
- Create: `frontend/src/layouts/BlankLayout.tsx`
- Create: `frontend/src/layouts/BasicLayout.tsx`
- Create: `frontend/src/pages/Login/index.tsx`
- Create: `frontend/src/pages/Dashboard/index.tsx`

- [ ] **Step 1: Create main.tsx**

Write `frontend/src/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app';
import './styles/global.css';
import './global';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 2: Create app.tsx（Teal 主题，无通知轮询）**

Write `frontend/src/app.tsx`:

```tsx
import { useEffect } from 'react';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { BrowserRouter } from 'react-router-dom';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';

import useAuthStore from '@/stores/useAuthStore';
import AppRoutes from './routes';

dayjs.locale('zh-cn');

const themeConfig = {
  token: {
    colorPrimary: '#0d9488',
    colorSuccess: '#10B981',
    colorWarning: '#D97706',
    colorError: '#EF4444',
    colorInfo: '#0d9488',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f1f5f9',
    colorBorder: '#e2e8f0',
    colorBorderSecondary: '#e2e8f0',
    colorText: '#0f172a',
    colorTextSecondary: '#475569',
    colorTextTertiary: '#94a3b8',
    borderRadius: 8,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 14,
    controlHeight: 36,
    boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
  },
  components: {
    Button: { borderRadius: 8, controlHeight: 36, fontWeight: 500 },
    Card: { borderRadiusLG: 14 },
    Input: { borderRadius: 8, controlHeight: 36 },
    Select: { borderRadius: 8, controlHeight: 36 },
    Table: { borderRadius: 14, headerBg: 'transparent', headerColor: '#94a3b8' },
    Menu: { darkItemBg: 'transparent', darkSubMenuItemBg: 'rgba(0,0,0,0.15)' },
  },
};

export default function App() {
  const { isLoggedIn, fetchCurrentUser } = useAuthStore();

  useEffect(() => {
    if (isLoggedIn) {
      fetchCurrentUser();
    }
  }, [isLoggedIn, fetchCurrentUser]);

  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      <AntdApp>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}
```

- [ ] **Step 3: Create routes.tsx**

Write `frontend/src/routes.tsx`:

```tsx
import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import BlankLayout from '@/layouts/BlankLayout';
import BasicLayout from '@/layouts/BasicLayout';

const Login = lazy(() => import('@/pages/Login'));
const Dashboard = lazy(() => import('@/pages/Dashboard'));

export default function AppRoutes() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route element={<BlankLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>
        <Route element={<BasicLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
```

- [ ] **Step 4: Create BlankLayout.tsx**

Write `frontend/src/layouts/BlankLayout.tsx`:

```tsx
import { Outlet } from 'react-router-dom';

export default function BlankLayout() {
  return (
    <div style={{ minHeight: '100vh' }}>
      <Outlet />
    </div>
  );
}
```

- [ ] **Step 5: Create BasicLayout.tsx（Teal 主题，精简菜单）**

Write `frontend/src/layouts/BasicLayout.tsx`:

```tsx
import { useEffect, useState, useCallback } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Suspense } from 'react';
import { Layout, Menu, Avatar, Dropdown, Space, Typography, Spin } from 'antd';
import {
  DashboardOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';

import useAuthStore from '@/stores/useAuthStore';
import { isAuthenticated } from '@/utils/auth';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
];

export default function BasicLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser, logout } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login', { replace: true });
    }
  }, [navigate]);

  const handleMenuClick = useCallback(
    ({ key }: { key: string }) => navigate(key),
    [navigate],
  );

  const handleLogout = useCallback(async () => {
    await logout();
    navigate('/login', { replace: true });
  }, [logout, navigate]);

  const siderWidth = collapsed ? 80 : 240;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={240}
        collapsedWidth={80}
        collapsed={collapsed}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
          background: '#042f2e',
          borderRight: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        {/* Logo */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            padding: '0 20px',
            gap: 12,
            borderBottom: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #0d9488, #14b8a6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              boxShadow: '0 4px 12px rgba(13, 148, 136, 0.35)',
            }}
          >
            <span style={{ fontSize: 16, color: '#fff', fontWeight: 700 }}>B</span>
          </div>
          {!collapsed && (
            <div>
              <div style={{ color: '#fff', fontSize: 15, fontWeight: 600, lineHeight: 1.3 }}>
                招投标管理平台
              </div>
              <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 11 }}>
                Bid Management
              </div>
            </div>
          )}
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ background: 'transparent', borderRight: 'none', marginTop: 8 }}
        />
      </Sider>

      <Layout style={{ marginLeft: siderWidth, transition: 'margin-left 0.2s' }}>
        {/* Header */}
        <Header
          style={{
            padding: '0 32px',
            height: 64,
            lineHeight: '64px',
            background: 'rgba(255, 255, 255, 0.85)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #e2e8f0',
            position: 'sticky',
            top: 0,
            zIndex: 9,
          }}
        >
          <Space>
            <div
              onClick={() => setCollapsed(!collapsed)}
              style={{ cursor: 'pointer', fontSize: 18, color: '#475569', padding: '4px 8px' }}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </div>
            <Text strong style={{ fontSize: 16 }}>
              {menuItems.find((m) => m.key === location.pathname)?.label || ''}
            </Text>
          </Space>

          <Dropdown
            menu={{
              items: [
                { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
              ],
            }}
            placement="bottomRight"
          >
            <Space style={{ cursor: 'pointer' }}>
              <Avatar size={32} icon={<UserOutlined />} style={{ background: '#0d9488' }} />
              <Text style={{ color: '#475569' }}>{currentUser?.real_name || '用户'}</Text>
            </Space>
          </Dropdown>
        </Header>

        {/* Content */}
        <Content style={{ margin: 24 }}>
          <Suspense fallback={<div style={{ textAlign: 'center', padding: 100 }}><Spin size="large" /></div>}>
            <Outlet />
          </Suspense>
        </Content>
      </Layout>
    </Layout>
  );
}
```

- [ ] **Step 6: Create Login page（Teal 主题）**

Write `frontend/src/pages/Login/index.tsx`:

```tsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Checkbox, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import useAuthStore from '@/stores/useAuthStore';
import { SYSTEM_NAME } from '@/constants';
import { isAuthenticated } from '@/utils/auth';

const REMEMBER_KEY = 'bid_system_remember_username';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loading } = useAuthStore();
  const [form] = Form.useForm();

  useEffect(() => {
    if (isAuthenticated()) {
      navigate('/', { replace: true });
      return;
    }
    const saved = localStorage.getItem(REMEMBER_KEY);
    if (saved) {
      form.setFieldsValue({ username: saved, remember: true });
    }
  }, [navigate, form]);

  const handleSubmit = async (values: LoginParams & { remember?: boolean }) => {
    try {
      await login({ username: values.username, password: values.password });
      if (values.remember) {
        localStorage.setItem(REMEMBER_KEY, values.username);
      } else {
        localStorage.removeItem(REMEMBER_KEY);
      }
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch {
      message.error('登录失败，请检查用户名和密码');
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#042f2e',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Teal glow orbs */}
      <div
        style={{
          position: 'absolute',
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(13, 148, 136, 0.3) 0%, transparent 70%)',
          top: '-10%',
          right: '-5%',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(20, 184, 166, 0.25) 0%, transparent 70%)',
          bottom: '-10%',
          left: '-5%',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          width: 400,
          padding: '48px 40px 36px',
          background: 'rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: 20,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 25px 50px rgba(0, 0, 0, 0.3)',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #0d9488, #14b8a6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              boxShadow: '0 8px 24px rgba(13, 148, 136, 0.35)',
            }}
          >
            <span style={{ fontSize: 22, color: '#fff', fontWeight: 700 }}>B</span>
          </div>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              background: 'linear-gradient(135deg, #0d9488, #14b8a6)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              marginBottom: 6,
            }}
          >
            {SYSTEM_NAME}
          </h1>
          <p style={{ color: 'rgba(255, 255, 255, 0.45)', fontSize: 13, margin: 0 }}>
            请登录您的账户以继续
          </p>
        </div>

        <Form form={form} onFinish={handleSubmit} autoComplete="off">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]} style={{ marginBottom: 20 }}>
            <Input
              prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
              placeholder="用户名"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 10,
                height: 46,
                color: '#fff',
                fontSize: 14,
              }}
            />
          </Form.Item>

          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]} style={{ marginBottom: 20 }}>
            <Input.Password
              prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
              placeholder="密码"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 10,
                height: 46,
                color: '#fff',
                fontSize: 14,
              }}
            />
          </Form.Item>

          <Form.Item name="remember" valuePropName="checked" style={{ marginBottom: 24 }}>
            <Checkbox style={{ color: 'rgba(255,255,255,0.5)' }}>记住我</Checkbox>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 46,
                borderRadius: 10,
                fontSize: 15,
                fontWeight: 600,
                background: 'linear-gradient(135deg, #0d9488, #14b8a6)',
                border: 'none',
                boxShadow: '0 4px 14px rgba(13, 148, 136, 0.35)',
              }}
            >
              登 录
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Create Dashboard placeholder**

Write `frontend/src/pages/Dashboard/index.tsx`:

```tsx
import { Card, Typography } from 'antd';
import { DashboardOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

export default function DashboardPage() {
  return (
    <Card>
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <DashboardOutlined style={{ fontSize: 48, color: '#0d9488', marginBottom: 16 }} />
        <Title level={3}>招投标管理平台</Title>
        <Text type="secondary">仪表盘开发中，Phase 1 将实现经营大盘数据</Text>
      </div>
    </Card>
  );
}
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/main.tsx frontend/src/app.tsx frontend/src/routes.tsx frontend/src/layouts/ frontend/src/pages/
git commit -m "feat: add layouts, login page, dashboard placeholder with Teal theme"
```

---

## Task 9: 端到端验证

**Files:** None (verification only)

- [ ] **Step 1: Start backend**

```bash
cd backend && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002 &
sleep 2
curl http://localhost:8002/api/health
```

Expected: `{"code":200,"message":"ok","data":{"status":"healthy"},...}`

- [ ] **Step 2: Start frontend**

```bash
cd frontend && npm run dev &
sleep 3
```

Expected: Vite 启动成功，端口 5180

- [ ] **Step 3: Verify login flow in browser**

打开 `http://localhost:5180`：
1. 应自动跳转到登录页
2. 看到 Teal 科技青主题的登录页面（深色背景+青色光晕）
3. 输入 `admin / admin123`
4. 点击登录 → 进入仪表盘占位页
5. 看到左侧深色侧边栏，Logo 显示"招投标管理平台"
6. 右上角显示"系统管理员"

- [ ] **Step 4: TypeScript 编译检查**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无错误

- [ ] **Step 5: Vite 构建检查**

```bash
cd frontend && npm run build
```

Expected: 构建成功，输出到 `dist/`

- [ ] **Step 6: Stop services, final commit**

```bash
kill %1 %2 2>/dev/null
git add -A
git commit -m "feat: Phase 0 scaffold complete - bid management platform skeleton"
```

---

## Verification Checklist

| # | 验收项 | 命令/操作 |
|---|---|---|
| 1 | 后端启动成功 | `uvicorn app.main:app --port 8002` |
| 2 | 健康检查通过 | `curl localhost:8002/api/health` → 200 |
| 3 | 登录接口正常 | `curl -X POST .../auth/login` → access_token |
| 4 | /me 接口正常 | `curl -H "Authorization: Bearer ..." .../auth/me` → user info |
| 5 | 前端启动成功 | `npm run dev` → port 5180 |
| 6 | 登录页可访问 | 浏览器 → localhost:5180 → 登录页 |
| 7 | 登录流程正常 | admin/admin123 → 仪表盘 |
| 8 | TS 编译通过 | `npx tsc --noEmit` → 0 errors |
| 9 | Vite 构建通过 | `npm run build` → dist/ |
