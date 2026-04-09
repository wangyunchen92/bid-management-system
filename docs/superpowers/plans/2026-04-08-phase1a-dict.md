# Phase 1a: 数据字典模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现数据字典的增删改查（后端 9 个 API + 前端管理页面），并预置 8 个标书业务字典。

**Architecture:** 后端新增 system router（字典 CRUD），复用已有的 common 模块（response/exceptions/pagination/deps）。前端新增数据字典管理页面（左右分栏），修改路由和侧边栏菜单。新增 require_super_admin 权限依赖。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, Ant Design (Card/List/Table/Modal/Form), Zustand

---

## File Map

### Backend

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/system.py` | Modify | 新增 SysDictType、SysDictItem 模型 |
| `backend/app/schemas/system.py` | Create | 字典类型和字典项的 Pydantic Schema |
| `backend/app/services/system_service.py` | Create | 字典 CRUD 业务逻辑 |
| `backend/app/routers/system.py` | Create | /api/v1/system/* 路由 |
| `backend/app/common/deps.py` | Modify | 新增 require_super_admin 依赖 |
| `backend/app/main.py` | Modify | 注册 system router + 初始化字典数据 |

### Frontend

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/types/api.ts` | Modify | 新增 DictType、DictItem 类型 |
| `frontend/src/constants/api.ts` | Modify | 新增 SYSTEM_API 字典路径 |
| `frontend/src/services/system.ts` | Create | 字典 API 调用 |
| `frontend/src/stores/useDictStore.ts` | Create | 字典缓存 Store |
| `frontend/src/pages/System/Dict/index.tsx` | Create | 数据字典管理页面 |
| `frontend/src/layouts/BasicLayout.tsx` | Modify | 侧边栏新增系统管理菜单 |
| `frontend/src/routes.tsx` | Modify | 新增 /system/dict 路由 |

---

## Task 1: 后端模型和 Schema

**Files:**
- Modify: `backend/app/models/system.py`
- Create: `backend/app/schemas/system.py`

- [ ] **Step 1: Add SysDictType and SysDictItem to models/system.py**

在 `backend/app/models/system.py` 文件末尾追加：

```python
from sqlalchemy import BigInteger, Integer, func


class SysDictType(BaseModel):
    """数据字典类型表"""
    __tablename__ = "sys_dict_type"

    dict_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dict_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")


class SysDictItem(Base):
    """数据字典项表"""
    __tablename__ = "sys_dict_item"

    id: Mapped[int] = mapped_column(Integer if settings.DB_TYPE == "sqlite" else BigInteger, primary_key=True, autoincrement=True)
    dict_type_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    item_label: Mapped[str] = mapped_column(String(100), nullable=False)
    item_value: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
```

需要在文件顶部的 import 中补充：

```python
from app.config import settings
from app.database import Base
```

（注意：`SysDictType` 继承 `BaseModel` 获得 `id`, `is_deleted`, `created_at` 等；`SysDictItem` 直接继承 `Base`，无 `is_deleted`）

- [ ] **Step 2: Create schemas/system.py**

Write `backend/app/schemas/system.py`:

```python
"""
系统管理 Schema — 数据字典
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ========== 字典类型 ==========

class DictTypeCreate(BaseModel):
    dict_name: str = Field(..., max_length=100)
    dict_code: str = Field(..., max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    status: int = Field(default=1)


class DictTypeUpdate(BaseModel):
    dict_name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    status: Optional[int] = Field(default=None)


class DictTypeResponse(BaseModel):
    id: int
    dict_name: str
    dict_code: str
    description: Optional[str] = None
    status: int = 1
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ========== 字典项 ==========

class DictItemCreate(BaseModel):
    item_label: str = Field(..., max_length=100)
    item_value: str = Field(..., max_length=100)
    sort_order: int = Field(default=0)
    status: int = Field(default=1)
    description: Optional[str] = Field(default=None, max_length=255)


class DictItemUpdate(BaseModel):
    item_label: Optional[str] = Field(default=None, max_length=100)
    item_value: Optional[str] = Field(default=None, max_length=100)
    sort_order: Optional[int] = Field(default=None)
    status: Optional[int] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=255)


class DictItemResponse(BaseModel):
    id: int
    dict_type_id: int
    item_label: str
    item_value: str
    sort_order: int = 0
    status: int = 1
    description: Optional[str] = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Verify models import**

```bash
cd /Users/wangyunchen/agents/标书系统/backend && python3 -c "from app.models.system import SysDictType, SysDictItem; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add backend/app/models/system.py backend/app/schemas/system.py
git commit -m "feat(dict): add SysDictType/SysDictItem models and schemas"
```

---

## Task 2: 后端权限依赖 + Service

**Files:**
- Modify: `backend/app/common/deps.py`
- Create: `backend/app/services/system_service.py`

- [ ] **Step 1: Add require_super_admin to deps.py**

在 `backend/app/common/deps.py` 文件末尾追加：

```python
async def require_super_admin(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """要求当前用户是超级管理员"""
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
    if user.role != "SUPER_ADMIN":
        from app.common.exceptions import ForbiddenException
        raise ForbiddenException("需要超级管理员权限")
    return user_id
```

需要在文件顶部导入补充 `ForbiddenException`（如果尚未导入）。

- [ ] **Step 2: Create services/system_service.py**

Write `backend/app/services/system_service.py`:

```python
"""
系统管理服务 — 数据字典
"""

from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import BusinessException, DuplicateException, NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.system import SysDictType, SysDictItem
from app.schemas.system import (
    DictTypeCreate, DictTypeUpdate, DictTypeResponse,
    DictItemCreate, DictItemUpdate, DictItemResponse,
)


class SystemService:

    # ========== 字典类型 ==========

    async def list_dict_types(self, db: AsyncSession, params: PaginationParams) -> dict:
        query = select(SysDictType).where(SysDictType.is_deleted == 0)
        result = await paginate(db, query, params, sort_column=SysDictType.id)
        result["items"] = [DictTypeResponse.model_validate(t).model_dump() for t in result["items"]]
        return result

    async def create_dict_type(self, db: AsyncSession, data: DictTypeCreate, user_id: int) -> dict:
        existing = await db.execute(
            select(SysDictType).where(SysDictType.dict_code == data.dict_code, SysDictType.is_deleted == 0)
        )
        if existing.scalar_one_or_none():
            raise DuplicateException(f"字典编码 '{data.dict_code}' 已存在")

        dict_type = SysDictType(**data.model_dump(), created_by=user_id, updated_by=user_id)
        db.add(dict_type)
        await db.flush()
        await db.refresh(dict_type)
        return DictTypeResponse.model_validate(dict_type).model_dump()

    async def update_dict_type(self, db: AsyncSession, dict_type_id: int, data: DictTypeUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(SysDictType).where(SysDictType.id == dict_type_id, SysDictType.is_deleted == 0)
        )
        dict_type = result.scalar_one_or_none()
        if dict_type is None:
            raise NotFoundException("字典类型不存在")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(dict_type, key, value)
        await db.flush()
        await db.refresh(dict_type)
        return DictTypeResponse.model_validate(dict_type).model_dump()

    async def delete_dict_type(self, db: AsyncSession, dict_type_id: int, user_id: int) -> None:
        result = await db.execute(
            select(SysDictType).where(SysDictType.id == dict_type_id, SysDictType.is_deleted == 0)
        )
        dict_type = result.scalar_one_or_none()
        if dict_type is None:
            raise NotFoundException("字典类型不存在")

        count_result = await db.execute(
            select(func.count()).select_from(SysDictItem).where(SysDictItem.dict_type_id == dict_type_id)
        )
        if (count_result.scalar() or 0) > 0:
            raise BusinessException("该字典类型下存在字典项，请先删除字典项")

        dict_type.is_deleted = 1
        dict_type.updated_by = user_id
        await db.flush()

    # ========== 字典项 ==========

    async def list_dict_items(self, db: AsyncSession, dict_type_id: int) -> List[dict]:
        result = await db.execute(
            select(SysDictType).where(SysDictType.id == dict_type_id, SysDictType.is_deleted == 0)
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundException("字典类型不存在")

        items_result = await db.execute(
            select(SysDictItem)
            .where(SysDictItem.dict_type_id == dict_type_id)
            .order_by(SysDictItem.sort_order.asc(), SysDictItem.id.asc())
        )
        return [DictItemResponse.model_validate(item).model_dump() for item in items_result.scalars().all()]

    async def create_dict_item(self, db: AsyncSession, dict_type_id: int, data: DictItemCreate, user_id: int) -> dict:
        type_result = await db.execute(
            select(SysDictType).where(SysDictType.id == dict_type_id, SysDictType.is_deleted == 0)
        )
        if type_result.scalar_one_or_none() is None:
            raise NotFoundException("字典类型不存在")

        dup_result = await db.execute(
            select(func.count()).select_from(SysDictItem).where(
                SysDictItem.dict_type_id == dict_type_id,
                SysDictItem.item_value == data.item_value,
            )
        )
        if (dup_result.scalar() or 0) > 0:
            raise DuplicateException(f"字典项值 '{data.item_value}' 在该字典类型下已存在")

        item = SysDictItem(**data.model_dump(), dict_type_id=dict_type_id)
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return DictItemResponse.model_validate(item).model_dump()

    async def update_dict_item(self, db: AsyncSession, item_id: int, data: DictItemUpdate, user_id: int) -> dict:
        result = await db.execute(select(SysDictItem).where(SysDictItem.id == item_id))
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundException("字典项不存在")

        if data.item_value is not None:
            dup_result = await db.execute(
                select(func.count()).select_from(SysDictItem).where(
                    SysDictItem.dict_type_id == item.dict_type_id,
                    SysDictItem.item_value == data.item_value,
                    SysDictItem.id != item_id,
                )
            )
            if (dup_result.scalar() or 0) > 0:
                raise DuplicateException(f"字典项值 '{data.item_value}' 在该字典类型下已存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)
        await db.flush()
        await db.refresh(item)
        return DictItemResponse.model_validate(item).model_dump()

    async def delete_dict_item(self, db: AsyncSession, item_id: int, user_id: int) -> None:
        result = await db.execute(select(SysDictItem).where(SysDictItem.id == item_id))
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundException("字典项不存在")
        await db.delete(item)
        await db.flush()

    async def get_dict_by_code(self, db: AsyncSession, dict_code: str) -> List[dict]:
        items_result = await db.execute(
            select(SysDictItem)
            .join(SysDictType, SysDictType.id == SysDictItem.dict_type_id)
            .where(
                SysDictType.dict_code == dict_code,
                SysDictType.is_deleted == 0,
                SysDictType.status == 1,
                SysDictItem.status == 1,
            )
            .order_by(SysDictItem.sort_order.asc(), SysDictItem.id.asc())
        )
        return [DictItemResponse.model_validate(item).model_dump() for item in items_result.scalars().all()]


system_service = SystemService()
```

- [ ] **Step 3: Verify imports**

```bash
cd /Users/wangyunchen/agents/标书系统/backend && python3 -c "from app.services.system_service import system_service; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add backend/app/common/deps.py backend/app/services/system_service.py
git commit -m "feat(dict): add require_super_admin dep and system service"
```

---

## Task 3: 后端 Router + main.py 注册 + 初始化数据

**Files:**
- Create: `backend/app/routers/system.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create routers/system.py**

Write `backend/app/routers/system.py`:

```python
"""
系统管理路由 /api/v1/system/*
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.system import (
    DictTypeCreate, DictTypeUpdate,
    DictItemCreate, DictItemUpdate,
)
from app.services.system_service import system_service

router = APIRouter()


# ========== 字典类型 ==========

@router.get("/dict-types", summary="字典类型列表")
async def list_dict_types(
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    data = await system_service.list_dict_types(db, params)
    return page_response(
        items=data["items"],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
    )


@router.post("/dict-types", summary="创建字典类型")
async def create_dict_type(
    request: DictTypeCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    data = await system_service.create_dict_type(db, request, user_id)
    return success(data=data, message="字典类型创建成功")


@router.put("/dict-types/{dict_type_id}", summary="更新字典类型")
async def update_dict_type(
    dict_type_id: int,
    request: DictTypeUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    data = await system_service.update_dict_type(db, dict_type_id, request, user_id)
    return success(data=data, message="字典类型更新成功")


@router.delete("/dict-types/{dict_type_id}", summary="删除字典类型")
async def delete_dict_type(
    dict_type_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.delete_dict_type(db, dict_type_id, user_id)
    return success(message="字典类型删除成功")


# ========== 字典项 ==========

@router.get("/dict-types/{dict_type_id}/items", summary="字典项列表")
async def list_dict_items(
    dict_type_id: int,
    db: AsyncSession = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    data = await system_service.list_dict_items(db, dict_type_id)
    return success(data=data)


@router.post("/dict-types/{dict_type_id}/items", summary="创建字典项")
async def create_dict_item(
    dict_type_id: int,
    request: DictItemCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    data = await system_service.create_dict_item(db, dict_type_id, request, user_id)
    return success(data=data, message="字典项创建成功")


@router.put("/dict-items/{item_id}", summary="更新字典项")
async def update_dict_item(
    item_id: int,
    request: DictItemUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    data = await system_service.update_dict_item(db, item_id, request, user_id)
    return success(data=data, message="字典项更新成功")


@router.delete("/dict-items/{item_id}", summary="删除字典项")
async def delete_dict_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.delete_dict_item(db, item_id, user_id)
    return success(message="字典项删除成功")


# ========== 按编码查字典 ==========

@router.get("/dicts/{dict_code}", summary="按编码查字典项")
async def get_dict_by_code(
    dict_code: str,
    db: AsyncSession = Depends(get_db),
    _user_id: int = Depends(get_current_user_id),
):
    data = await system_service.get_dict_by_code(db, dict_code)
    return success(data=data)
```

- [ ] **Step 2: Modify main.py — register system router**

在 `backend/app/main.py` 中，在 `from app.routers import auth` 行之后添加：

```python
from app.routers import system
```

在 `app.include_router(auth.router, ...)` 行之后添加：

```python
app.include_router(system.router, prefix="/api/v1/system", tags=["系统管理"])
```

- [ ] **Step 3: Modify main.py — add dict initialization**

在 `backend/app/main.py` 的 `_init_base_data` 函数中，在 `await session.commit()` 之后（admin 创建逻辑之后），添加字典初始化调用。将整个 `_init_base_data` 函数替换为：

```python
async def _init_base_data():
    from sqlalchemy import select
    from app.models.system import SysUser, SysDictType, SysDictItem
    from app.common.security import hash_password

    async with async_session_factory() as session:
        # 创建默认管理员
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

        # 初始化数据字典
        result = await session.execute(select(SysDictType).limit(1))
        if not result.scalar_one_or_none():
            await _init_dict_data(session)
            logger.info("预置数据字典已创建")


async def _init_dict_data(session):
    from app.models.system import SysDictType, SysDictItem

    DICTS = {
        "tender_method": ("招标方式", [
            ("公开招标", "PUBLIC"), ("邀请招标", "INVITE"), ("竞争性谈判", "NEGOTIATE"),
            ("询价", "INQUIRY"), ("单一来源", "SINGLE"),
        ]),
        "tender_source": ("信息来源", [
            ("政府采购网", "GOV"), ("招标信息网", "BID_INFO"), ("企业直邀", "DIRECT"),
            ("中介推荐", "AGENT"), ("其他", "OTHER"),
        ]),
        "bid_status": ("投标状态", [
            ("待评估", "PENDING"), ("已决策-投标", "DECIDED_BID"), ("已决策-放弃", "DECIDED_GIVE_UP"),
            ("编制中", "COMPOSING"), ("已提交", "SUBMITTED"), ("已开标", "OPENED"),
        ]),
        "decision_result": ("决策结果", [
            ("通过", "PASS"), ("不通过", "REJECT"), ("待定", "PENDING"),
        ]),
        "opening_result": ("开标结果", [
            ("中标", "WIN"), ("未中标", "LOSE"), ("废标", "INVALID"), ("流标", "ABORTED"),
        ]),
        "doc_type": ("标书文档类型", [
            ("技术方案", "TECH"), ("商务报价", "COMMERCIAL"), ("资质文件", "QUALIFICATION"),
            ("承诺函", "COMMITMENT"), ("其他", "OTHER"),
        ]),
        "cert_type": ("资质证书类型", [
            ("营业执照", "BUSINESS_LICENSE"), ("资质证书", "QUALIFICATION"), ("ISO认证", "ISO"),
            ("安全生产许可证", "SAFETY"), ("其他", "OTHER"),
        ]),
        "urgency": ("紧急程度", [
            ("正常", "NORMAL"), ("紧急", "URGENT"), ("特急", "CRITICAL"),
        ]),
    }

    for code, (name, items) in DICTS.items():
        dict_type = SysDictType(dict_name=name, dict_code=code, status=1)
        session.add(dict_type)
        await session.flush()
        for i, (label, value) in enumerate(items):
            session.add(SysDictItem(
                dict_type_id=dict_type.id,
                item_label=label,
                item_value=value,
                sort_order=i + 1,
                status=1,
            ))
    await session.commit()
```

- [ ] **Step 4: Delete old SQLite DB (schema changed) and test**

```bash
rm -f /Users/wangyunchen/agents/标书系统/backend/data/bid.db
cd /Users/wangyunchen/agents/标书系统/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8002 &
sleep 3
```

Test health:
```bash
curl -s http://localhost:8002/api/health
```

Test dict by code:
```bash
TOKEN=$(curl -s -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/system/dicts/tender_method
```

Expected: 返回 5 个招标方式字典项

Test dict type list:
```bash
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/system/dict-types?page=1&page_size=20"
```

Expected: 返回 8 个字典类型（分页格式）

Test create dict type:
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8002/api/v1/system/dict-types -d '{"dict_name":"测试类型","dict_code":"test_type"}'
```

Expected: 返回创建成功

Test delete protection:
```bash
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/system/dict-types/1
```

Expected: 返回 "该字典类型下存在字典项，请先删除字典项"

Stop server:
```bash
kill %1 2>/dev/null || pkill -f "uvicorn app.main:app" 2>/dev/null
```

- [ ] **Step 5: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add backend/app/routers/system.py backend/app/main.py
git commit -m "feat(dict): add system router with 9 dict APIs and init data"
```

---

## Task 4: 前端类型、常量、API 层

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/constants/api.ts`
- Create: `frontend/src/services/system.ts`

- [ ] **Step 1: Add DictType and DictItem to types/api.ts**

在 `frontend/src/types/api.ts` 文件末尾追加：

```typescript
/** 字典类型 */
interface DictType {
  id: number;
  dict_name: string;
  dict_code: string;
  description?: string;
  status: number;
  created_at?: string;
}

/** 字典项 */
interface DictItem {
  id: number;
  dict_type_id: number;
  item_label: string;
  item_value: string;
  sort_order: number;
  status: number;
  description?: string;
}
```

- [ ] **Step 2: Add SYSTEM_API to constants/api.ts**

在 `frontend/src/constants/api.ts` 文件末尾追加：

```typescript

export const SYSTEM_API = {
  DICT_TYPE_LIST: `${API_PREFIX}/system/dict-types`,
  DICT_TYPE_CREATE: `${API_PREFIX}/system/dict-types`,
  DICT_TYPE_UPDATE: (id: number) => `${API_PREFIX}/system/dict-types/${id}`,
  DICT_TYPE_DELETE: (id: number) => `${API_PREFIX}/system/dict-types/${id}`,
  DICT_ITEM_LIST: (typeId: number) => `${API_PREFIX}/system/dict-types/${typeId}/items`,
  DICT_ITEM_CREATE: (typeId: number) => `${API_PREFIX}/system/dict-types/${typeId}/items`,
  DICT_ITEM_UPDATE: (id: number) => `${API_PREFIX}/system/dict-items/${id}`,
  DICT_ITEM_DELETE: (id: number) => `${API_PREFIX}/system/dict-items/${id}`,
  DICT_BY_CODE: (code: string) => `${API_PREFIX}/system/dicts/${code}`,
} as const;
```

- [ ] **Step 3: Create services/system.ts**

Write `frontend/src/services/system.ts`:

```typescript
import { get, post, put, del } from '@/utils/request';
import { SYSTEM_API } from '@/constants/api';

// ========== 字典类型 ==========

export function getDictTypeList(params?: Record<string, unknown>) {
  return get<PaginatedData<DictType>>(SYSTEM_API.DICT_TYPE_LIST, params);
}

export function createDictType(data: Partial<DictType>) {
  return post<DictType>(SYSTEM_API.DICT_TYPE_CREATE, data);
}

export function updateDictType(id: number, data: Partial<DictType>) {
  return put<DictType>(SYSTEM_API.DICT_TYPE_UPDATE(id), data);
}

export function deleteDictType(id: number) {
  return del(SYSTEM_API.DICT_TYPE_DELETE(id));
}

// ========== 字典项 ==========

export function getDictItemList(typeId: number) {
  return get<DictItem[]>(SYSTEM_API.DICT_ITEM_LIST(typeId));
}

export function createDictItem(typeId: number, data: Partial<DictItem>) {
  return post<DictItem>(SYSTEM_API.DICT_ITEM_CREATE(typeId), data);
}

export function updateDictItem(id: number, data: Partial<DictItem>) {
  return put<DictItem>(SYSTEM_API.DICT_ITEM_UPDATE(id), data);
}

export function deleteDictItem(id: number) {
  return del(SYSTEM_API.DICT_ITEM_DELETE(id));
}

// ========== 按编码查字典 ==========

export function getDictByCode(code: string) {
  return get<DictItem[]>(SYSTEM_API.DICT_BY_CODE(code));
}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/types/api.ts frontend/src/constants/api.ts frontend/src/services/system.ts
git commit -m "feat(dict): add frontend types, API constants, and system service"
```

---

## Task 5: 前端 Dict Store

**Files:**
- Create: `frontend/src/stores/useDictStore.ts`

- [ ] **Step 1: Create useDictStore.ts**

Write `frontend/src/stores/useDictStore.ts`:

```typescript
import { create } from 'zustand';
import { getDictByCode } from '@/services/system';

interface DictStoreState {
  cache: Record<string, DictItem[]>;
  loading: Record<string, boolean>;
  getDictItems: (code: string) => Promise<DictItem[]>;
  clearCache: () => void;
}

const useDictStore = create<DictStoreState>((set, get) => ({
  cache: {},
  loading: {},

  getDictItems: async (code: string) => {
    const { cache, loading } = get();

    if (cache[code]) {
      return cache[code];
    }

    if (loading[code]) {
      return [];
    }

    set((state) => ({ loading: { ...state.loading, [code]: true } }));

    try {
      const res = await getDictByCode(code);
      const items = res.data;
      set((state) => ({
        cache: { ...state.cache, [code]: items },
        loading: { ...state.loading, [code]: false },
      }));
      return items;
    } catch {
      set((state) => ({ loading: { ...state.loading, [code]: false } }));
      return [];
    }
  },

  clearCache: () => set({ cache: {}, loading: {} }),
}));

export default useDictStore;
```

- [ ] **Step 2: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/stores/useDictStore.ts
git commit -m "feat(dict): add dict cache store"
```

---

## Task 6: 前端数据字典页面

**Files:**
- Create: `frontend/src/pages/System/Dict/index.tsx`

- [ ] **Step 1: Create the Dict page**

Write `frontend/src/pages/System/Dict/index.tsx`:

```tsx
import { useEffect, useState, useCallback } from 'react';
import {
  Card, List, Table, Button, Modal, Form, Input, Switch, InputNumber,
  Space, Tag, message, Popconfirm, Empty, Typography,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, BookOutlined } from '@ant-design/icons';
import {
  getDictTypeList, createDictType, updateDictType, deleteDictType,
  getDictItemList, createDictItem, updateDictItem, deleteDictItem,
} from '@/services/system';

const { Text } = Typography;

export default function DictPage() {
  // ========== 字典类型 ==========
  const [types, setTypes] = useState<DictType[]>([]);
  const [typesLoading, setTypesLoading] = useState(false);
  const [selectedType, setSelectedType] = useState<DictType | null>(null);
  const [typeModalOpen, setTypeModalOpen] = useState(false);
  const [editingType, setEditingType] = useState<DictType | null>(null);
  const [typeForm] = Form.useForm();

  // ========== 字典项 ==========
  const [items, setItems] = useState<DictItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<DictItem | null>(null);
  const [itemForm] = Form.useForm();

  // 加载字典类型
  const loadTypes = useCallback(async () => {
    setTypesLoading(true);
    try {
      const res = await getDictTypeList({ page: 1, page_size: 100 });
      setTypes(res.data.items);
    } finally {
      setTypesLoading(false);
    }
  }, []);

  // 加载字典项
  const loadItems = useCallback(async (typeId: number) => {
    setItemsLoading(true);
    try {
      const res = await getDictItemList(typeId);
      setItems(res.data);
    } finally {
      setItemsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTypes();
  }, [loadTypes]);

  useEffect(() => {
    if (selectedType) {
      loadItems(selectedType.id);
    } else {
      setItems([]);
    }
  }, [selectedType, loadItems]);

  // ========== 字典类型操作 ==========

  const handleCreateType = () => {
    setEditingType(null);
    typeForm.resetFields();
    typeForm.setFieldsValue({ status: true });
    setTypeModalOpen(true);
  };

  const handleEditType = (t: DictType) => {
    setEditingType(t);
    typeForm.setFieldsValue({ ...t, status: t.status === 1 });
    setTypeModalOpen(true);
  };

  const handleTypeSubmit = async () => {
    const values = await typeForm.validateFields();
    const data = { ...values, status: values.status ? 1 : 0 };

    if (editingType) {
      await updateDictType(editingType.id, data);
      message.success('更新成功');
    } else {
      await createDictType(data);
      message.success('创建成功');
    }
    setTypeModalOpen(false);
    loadTypes();
  };

  const handleDeleteType = async (id: number) => {
    try {
      await deleteDictType(id);
      message.success('删除成功');
      if (selectedType?.id === id) {
        setSelectedType(null);
      }
      loadTypes();
    } catch {
      // error handled by request interceptor
    }
  };

  // ========== 字典项操作 ==========

  const handleCreateItem = () => {
    setEditingItem(null);
    itemForm.resetFields();
    itemForm.setFieldsValue({ status: true, sort_order: 0 });
    setItemModalOpen(true);
  };

  const handleEditItem = (item: DictItem) => {
    setEditingItem(item);
    itemForm.setFieldsValue({ ...item, status: item.status === 1 });
    setItemModalOpen(true);
  };

  const handleItemSubmit = async () => {
    if (!selectedType) return;
    const values = await itemForm.validateFields();
    const data = { ...values, status: values.status ? 1 : 0 };

    if (editingItem) {
      await updateDictItem(editingItem.id, data);
      message.success('更新成功');
    } else {
      await createDictItem(selectedType.id, data);
      message.success('创建成功');
    }
    setItemModalOpen(false);
    loadItems(selectedType.id);
  };

  const handleDeleteItem = async (id: number) => {
    if (!selectedType) return;
    await deleteDictItem(id);
    message.success('删除成功');
    loadItems(selectedType.id);
  };

  // ========== 字典项表格列 ==========

  const itemColumns = [
    { title: '显示标签', dataIndex: 'item_label', key: 'item_label' },
    {
      title: '存储值', dataIndex: 'item_value', key: 'item_value',
      render: (v: string) => <code style={{ background: '#f1f5f9', padding: '2px 8px', borderRadius: 4, fontSize: 13 }}>{v}</code>,
    },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80, align: 'center' as const },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: number) => v === 1 ? <Tag color="success">启用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: unknown, record: DictItem) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditItem(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDeleteItem(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      {/* 左侧：字典类型列表 */}
      <Card
        title="字典类型"
        extra={<Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreateType}>新增</Button>}
        style={{ width: 280, flexShrink: 0 }}
        bodyStyle={{ padding: 0 }}
      >
        <List
          loading={typesLoading}
          dataSource={types}
          renderItem={(t) => (
            <List.Item
              onClick={() => setSelectedType(t)}
              style={{
                padding: '12px 16px',
                cursor: 'pointer',
                borderLeft: selectedType?.id === t.id ? '3px solid #0d9488' : '3px solid transparent',
                background: selectedType?.id === t.id ? 'rgba(13,148,136,0.06)' : 'transparent',
                transition: 'all 0.2s',
              }}
              actions={[
                <Button key="edit" type="link" size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); handleEditType(t); }} />,
                <Popconfirm key="del" title="确定删除？" onConfirm={(e) => { e?.stopPropagation(); handleDeleteType(t.id); }}>
                  <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={<BookOutlined style={{ color: '#0d9488', fontSize: 16 }} />}
                title={<Text style={{ fontSize: 13 }}>{t.dict_name}</Text>}
                description={<Text type="secondary" style={{ fontSize: 12 }}>{t.dict_code}</Text>}
              />
            </List.Item>
          )}
        />
      </Card>

      {/* 右侧：字典项表格 */}
      <Card
        title={selectedType ? `${selectedType.dict_name} 字典项` : '字典项'}
        extra={selectedType && <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleCreateItem}>新增</Button>}
        style={{ flex: 1 }}
      >
        {selectedType ? (
          <Table
            dataSource={items}
            columns={itemColumns}
            rowKey="id"
            loading={itemsLoading}
            pagination={false}
            size="middle"
          />
        ) : (
          <Empty description="请在左侧选择一个字典类型" style={{ padding: '60px 0' }} />
        )}
      </Card>

      {/* 字典类型弹窗 */}
      <Modal
        title={editingType ? '编辑字典类型' : '新增字典类型'}
        open={typeModalOpen}
        onCancel={() => setTypeModalOpen(false)}
        onOk={handleTypeSubmit}
        destroyOnClose
      >
        <Form form={typeForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="dict_name" label="类型名称" rules={[{ required: true, message: '请输入类型名称' }]}>
            <Input placeholder="如：招标方式" />
          </Form.Item>
          <Form.Item name="dict_code" label="类型编码" rules={[{ required: true, message: '请输入类型编码' }]}>
            <Input placeholder="如：tender_method" disabled={!!editingType} />
          </Form.Item>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
          <Form.Item name="description" label="备注">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 字典项弹窗 */}
      <Modal
        title={editingItem ? '编辑字典项' : '新增字典项'}
        open={itemModalOpen}
        onCancel={() => setItemModalOpen(false)}
        onOk={handleItemSubmit}
        destroyOnClose
      >
        <Form form={itemForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="item_label" label="显示标签" rules={[{ required: true, message: '请输入显示标签' }]}>
            <Input placeholder="如：公开招标" />
          </Form.Item>
          <Form.Item name="item_value" label="存储值" rules={[{ required: true, message: '请输入存储值' }]}>
            <Input placeholder="如：PUBLIC" disabled={!!editingItem} />
          </Form.Item>
          <Form.Item name="sort_order" label="排序号">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
          <Form.Item name="description" label="备注">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/pages/System/Dict/index.tsx
git commit -m "feat(dict): add data dictionary management page"
```

---

## Task 7: 前端路由和菜单更新

**Files:**
- Modify: `frontend/src/routes.tsx`
- Modify: `frontend/src/layouts/BasicLayout.tsx`

- [ ] **Step 1: Update routes.tsx**

Replace the entire `frontend/src/routes.tsx`:

```tsx
import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import BlankLayout from '@/layouts/BlankLayout';
import BasicLayout from '@/layouts/BasicLayout';

const Login = lazy(() => import('@/pages/Login'));
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Dict = lazy(() => import('@/pages/System/Dict'));

export default function AppRoutes() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route element={<BlankLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>
        <Route element={<BasicLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/system/dict" element={<Dict />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
```

- [ ] **Step 2: Update BasicLayout.tsx menuItems**

In `frontend/src/layouts/BasicLayout.tsx`, replace the `menuItems` array and add the `SettingOutlined` import.

Add `SettingOutlined` to the icon imports (line 6):

```tsx
import {
  DashboardOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
```

Replace the `menuItems` array:

```tsx
const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
  {
    key: '/system',
    icon: <SettingOutlined />,
    label: '系统管理',
    children: [
      { key: '/system/dict', label: '数据字典' },
    ],
  },
];
```

Also update the header title logic (line ~140) to handle nested menu items. Replace:

```tsx
{menuItems.find((m) => m.key === location.pathname)?.label || ''}
```

With:

```tsx
{(() => {
  for (const m of menuItems) {
    if (m.key === location.pathname) return m.label;
    if ('children' in m && m.children) {
      const child = m.children.find((c) => c.key === location.pathname);
      if (child) return child.label;
    }
  }
  return '';
})()}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/wangyunchen/agents/标书系统/frontend && npx tsc --noEmit
```

Expected: 0 errors

- [ ] **Step 4: Verify Vite build**

```bash
cd /Users/wangyunchen/agents/标书系统/frontend && npm run build
```

Expected: 构建成功

- [ ] **Step 5: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/routes.tsx frontend/src/layouts/BasicLayout.tsx
git commit -m "feat(dict): add dict route and system menu to sidebar"
```

---

## Task 8: 端到端验证

**Files:** None (verification only)

- [ ] **Step 1: Start backend**

```bash
rm -f /Users/wangyunchen/agents/标书系统/backend/data/bid.db
cd /Users/wangyunchen/agents/标书系统/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8002 &
sleep 3
```

- [ ] **Step 2: API tests (9 endpoints)**

```bash
TOKEN=$(curl -s -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# 1. 字典类型列表
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/system/dict-types?page=1&page_size=20" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Types: {d[\"data\"][\"total\"]} total')"

# 2. 按编码查字典
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/system/dicts/tender_method | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'tender_method items: {len(d[\"data\"])}')"

# 3. 创建字典类型
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8002/api/v1/system/dict-types -d '{"dict_name":"测试","dict_code":"test_e2e"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 4. 创建字典项
NEW_TYPE_ID=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/system/dict-types?page=1&page_size=100" | python3 -c "import sys,json; types=json.load(sys.stdin)['data']['items']; print([t['id'] for t in types if t['dict_code']=='test_e2e'][0])")
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "http://localhost:8002/api/v1/system/dict-types/$NEW_TYPE_ID/items" -d '{"item_label":"测试项","item_value":"TEST_VAL"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 5. 删除保护
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/system/dict-types/$NEW_TYPE_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 6. 删除字典项
ITEM_ID=$(curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/system/dict-types/$NEW_TYPE_ID/items" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/system/dict-items/$ITEM_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 7. 删除空类型
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/system/dict-types/$NEW_TYPE_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"
```

Expected output:
```
Types: 8 total
tender_method items: 5
字典类型创建成功
字典项创建成功
该字典类型下存在字典项，请先删除字典项
字典项删除成功
字典类型删除成功
```

- [ ] **Step 3: Frontend build verification**

```bash
cd /Users/wangyunchen/agents/标书系统/frontend && npx tsc --noEmit && npm run build
```

Expected: 两个命令都成功

- [ ] **Step 4: Stop backend, clean up**

```bash
kill %1 2>/dev/null || pkill -f "uvicorn app.main:app" 2>/dev/null
```

---

## Verification Checklist

| # | 验收项 | 对应 Task |
|---|---|---|
| 1 | 后端 9 个 API 可用 | Task 3, 8 |
| 2 | 启动后自动创建 8 个字典 | Task 3 |
| 3 | 前端数据字典页面渲染正常 | Task 6 |
| 4 | 左侧点击类型 → 右侧显示项 | Task 6 |
| 5 | 新增/编辑/删除类型和项均可操作 | Task 6 |
| 6 | 编码和存储值编辑时不可修改 | Task 6 |
| 7 | 删除有字典项的类型时拒绝 | Task 2, 3 |
| 8 | TypeScript 编译无错误 | Task 7 |
| 9 | Vite 构建成功 | Task 7 |
