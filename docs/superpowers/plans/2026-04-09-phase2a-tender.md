# Phase 2a: 招标管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现招标信息的 CRUD、状态管理、日历视图、统计概览和到期提醒，含后端 10 个 API 和前端 4 个页面。

**Architecture:** 新建 tender 业务模块（独立于 system/approval）。后端新建 models/tender.py, schemas/tender.py, services/tender_service.py, routers/tender.py。前端新增招标列表、表单、日历 3 个页面。金额用 DECIMAL(14,4)。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, Ant Design (Table/Form/Calendar/Card/Tag/Select/DatePicker)

---

## File Map

### Backend

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/tender.py` | Create | Tender 模型 |
| `backend/app/schemas/tender.py` | Create | 招标 Schema |
| `backend/app/services/tender_service.py` | Create | 招标业务逻辑 |
| `backend/app/routers/tender.py` | Create | /api/v1/tender/* 路由 |
| `backend/app/main.py` | Modify | 注册 tender router |

### Frontend

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/types/api.ts` | Modify | Tender 类型 |
| `frontend/src/constants/api.ts` | Modify | 招标 API 路径 |
| `frontend/src/services/tender.ts` | Create | 招标 API 调用 |
| `frontend/src/pages/Tender/List/index.tsx` | Create | 招标列表页 |
| `frontend/src/pages/Tender/Form/index.tsx` | Create | 新增/编辑表单页 |
| `frontend/src/pages/Tender/Calendar/index.tsx` | Create | 日历视图 |
| `frontend/src/layouts/BasicLayout.tsx` | Modify | 菜单新增招标管理 |
| `frontend/src/routes.tsx` | Modify | 新增路由 |

---

## Task 1: 后端模型 + Schema

**Files:**
- Create: `backend/app/models/tender.py`
- Create: `backend/app/schemas/tender.py`

- [ ] **Step 1: Create models/tender.py**

```python
"""
招标信息模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Tender(BaseModel):
    """招标信息表"""
    __tablename__ = "tender"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    tender_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tender_unit: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tender_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    info_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    budget_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    deposit_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    deposit_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reg_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    open_bid_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    follower_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

- [ ] **Step 2: Create schemas/tender.py**

```python
"""
招标 Schema
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TenderCreate(BaseModel):
    title: str = Field(..., max_length=200)
    tender_no: Optional[str] = Field(default=None, max_length=100)
    tender_unit: Optional[str] = Field(default=None, max_length=200)
    tender_method: Optional[str] = Field(default=None, max_length=50)
    info_source: Optional[str] = Field(default=None, max_length=50)
    province: Optional[str] = Field(default=None, max_length=50)
    city: Optional[str] = Field(default=None, max_length=50)
    budget_amount: Optional[Decimal] = Field(default=None)
    deposit_amount: Optional[Decimal] = Field(default=None)
    deposit_deadline: Optional[datetime] = Field(default=None)
    reg_deadline: Optional[datetime] = Field(default=None)
    open_bid_time: Optional[datetime] = Field(default=None)
    status: str = Field(default="PENDING")
    follower_id: Optional[int] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class TenderUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    tender_no: Optional[str] = Field(default=None, max_length=100)
    tender_unit: Optional[str] = Field(default=None, max_length=200)
    tender_method: Optional[str] = Field(default=None, max_length=50)
    info_source: Optional[str] = Field(default=None, max_length=50)
    province: Optional[str] = Field(default=None, max_length=50)
    city: Optional[str] = Field(default=None, max_length=50)
    budget_amount: Optional[Decimal] = Field(default=None)
    deposit_amount: Optional[Decimal] = Field(default=None)
    deposit_deadline: Optional[datetime] = Field(default=None)
    reg_deadline: Optional[datetime] = Field(default=None)
    open_bid_time: Optional[datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    follower_id: Optional[int] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class TenderResponse(BaseModel):
    id: int
    title: str
    tender_no: Optional[str] = None
    tender_unit: Optional[str] = None
    tender_method: Optional[str] = None
    info_source: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    budget_amount: Optional[float] = None
    deposit_amount: Optional[float] = None
    deposit_deadline: Optional[datetime] = None
    reg_deadline: Optional[datetime] = None
    open_bid_time: Optional[datetime] = None
    status: str = "PENDING"
    follower_id: Optional[int] = None
    follower_name: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., max_length=20)


class UpdateFollowerRequest(BaseModel):
    follower_id: int = Field(...)


class TenderCalendarItem(BaseModel):
    id: int
    title: str
    date: str
    type: str
    label: str


class TenderStats(BaseModel):
    total: int = 0
    pending: int = 0
    decided_bid: int = 0
    decided_give_up: int = 0
    composing: int = 0
    submitted: int = 0
    opened: int = 0
```

- [ ] **Step 3: Verify and commit**

```bash
cd /Users/wangyunchen/agents/标书系统/backend && python3 -c "from app.models.tender import Tender; print('OK')"
git add backend/app/models/tender.py backend/app/schemas/tender.py
git commit -m "feat(tender): add Tender model and schemas"
```

---

## Task 2: 后端 Service

**Files:**
- Create: `backend/app/services/tender_service.py`

- [ ] **Step 1: Create tender_service.py**

```python
"""
招标管理服务
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.tender import Tender
from app.models.system import SysUser
from app.schemas.tender import TenderCreate, TenderUpdate, TenderResponse, TenderCalendarItem, TenderStats


class TenderService:

    async def _get_follower_name(self, db: AsyncSession, follower_id: Optional[int]) -> Optional[str]:
        if not follower_id:
            return None
        result = await db.execute(select(SysUser.real_name).where(SysUser.id == follower_id))
        return result.scalar_one_or_none()

    async def _tender_to_dict(self, db: AsyncSession, tender: Tender) -> dict:
        d = TenderResponse.model_validate(tender).model_dump()
        d["follower_name"] = await self._get_follower_name(db, tender.follower_id)
        # Decimal → float for JSON
        if d.get("budget_amount") is not None:
            d["budget_amount"] = float(d["budget_amount"])
        if d.get("deposit_amount") is not None:
            d["deposit_amount"] = float(d["deposit_amount"])
        return d

    async def list_tenders(self, db: AsyncSession, params: PaginationParams,
                           keyword: Optional[str] = None, tender_method: Optional[str] = None,
                           info_source: Optional[str] = None, status: Optional[str] = None,
                           follower_id: Optional[int] = None,
                           start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        query = select(Tender).where(Tender.is_deleted == 0)

        if keyword:
            query = query.where(or_(Tender.title.contains(keyword), Tender.tender_no.contains(keyword)))
        if tender_method:
            query = query.where(Tender.tender_method == tender_method)
        if info_source:
            query = query.where(Tender.info_source == info_source)
        if status:
            query = query.where(Tender.status == status)
        if follower_id:
            query = query.where(Tender.follower_id == follower_id)
        if start_date:
            query = query.where(Tender.open_bid_time >= start_date)
        if end_date:
            query = query.where(Tender.open_bid_time <= end_date)

        result = await paginate(db, query, params, sort_column=Tender.id)
        items = []
        for t in result["items"]:
            items.append(await self._tender_to_dict(db, t))
        result["items"] = items
        return result

    async def create_tender(self, db: AsyncSession, data: TenderCreate, user_id: int) -> dict:
        tender = Tender(**data.model_dump(), created_by=user_id, updated_by=user_id)
        db.add(tender)
        await db.flush()
        await db.refresh(tender)
        return await self._tender_to_dict(db, tender)

    async def get_tender(self, db: AsyncSession, tender_id: int) -> dict:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")
        return await self._tender_to_dict(db, tender)

    async def update_tender(self, db: AsyncSession, tender_id: int, data: TenderUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(tender, key, value)
        await db.flush()
        await db.refresh(tender)
        return await self._tender_to_dict(db, tender)

    async def delete_tender(self, db: AsyncSession, tender_id: int, user_id: int) -> None:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")
        tender.is_deleted = 1
        tender.updated_by = user_id
        await db.flush()

    async def update_status(self, db: AsyncSession, tender_id: int, status: str, user_id: int) -> dict:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")
        tender.status = status
        tender.updated_by = user_id
        await db.flush()
        await db.refresh(tender)
        return await self._tender_to_dict(db, tender)

    async def update_follower(self, db: AsyncSession, tender_id: int, follower_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")
        tender.follower_id = follower_id
        tender.updated_by = user_id
        await db.flush()
        await db.refresh(tender)
        return await self._tender_to_dict(db, tender)

    async def get_calendar(self, db: AsyncSession, year: int, month: int) -> List[dict]:
        from calendar import monthrange
        start = datetime(year, month, 1)
        _, last_day = monthrange(year, month)
        end = datetime(year, month, last_day, 23, 59, 59)

        result = await db.execute(
            select(Tender).where(
                Tender.is_deleted == 0,
                or_(
                    Tender.reg_deadline.between(start, end),
                    Tender.deposit_deadline.between(start, end),
                    Tender.open_bid_time.between(start, end),
                )
            )
        )
        tenders = result.scalars().all()

        items = []
        for t in tenders:
            if t.reg_deadline and start <= t.reg_deadline <= end:
                items.append(TenderCalendarItem(
                    id=t.id, title=t.title,
                    date=t.reg_deadline.strftime("%Y-%m-%d"),
                    type="reg_deadline", label="报名截止",
                ).model_dump())
            if t.deposit_deadline and start <= t.deposit_deadline <= end:
                items.append(TenderCalendarItem(
                    id=t.id, title=t.title,
                    date=t.deposit_deadline.strftime("%Y-%m-%d"),
                    type="deposit_deadline", label="保证金截止",
                ).model_dump())
            if t.open_bid_time and start <= t.open_bid_time <= end:
                items.append(TenderCalendarItem(
                    id=t.id, title=t.title,
                    date=t.open_bid_time.strftime("%Y-%m-%d"),
                    type="open_bid", label="开标",
                ).model_dump())
        return items

    async def get_stats(self, db: AsyncSession) -> dict:
        result = await db.execute(
            select(Tender.status, func.count(Tender.id))
            .where(Tender.is_deleted == 0)
            .group_by(Tender.status)
        )
        status_counts = {row[0]: row[1] for row in result.all()}

        total = sum(status_counts.values())
        return TenderStats(
            total=total,
            pending=status_counts.get("PENDING", 0),
            decided_bid=status_counts.get("DECIDED_BID", 0),
            decided_give_up=status_counts.get("DECIDED_GIVE_UP", 0),
            composing=status_counts.get("COMPOSING", 0),
            submitted=status_counts.get("SUBMITTED", 0),
            opened=status_counts.get("OPENED", 0),
        ).model_dump()

    async def get_expiring(self, db: AsyncSession) -> List[dict]:
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=7)

        result = await db.execute(
            select(Tender).where(
                Tender.is_deleted == 0,
                Tender.status.in_(["PENDING", "DECIDED_BID", "COMPOSING"]),
                or_(
                    Tender.reg_deadline.between(now, deadline),
                    Tender.deposit_deadline.between(now, deadline),
                    Tender.open_bid_time.between(now, deadline),
                )
            ).order_by(Tender.reg_deadline.asc())
        )
        items = []
        for t in result.scalars().all():
            items.append(await self._tender_to_dict(db, t))
        return items


tender_service = TenderService()
```

- [ ] **Step 2: Verify and commit**

```bash
cd /Users/wangyunchen/agents/标书系统/backend && python3 -c "from app.services.tender_service import tender_service; print('OK')"
git add backend/app/services/tender_service.py
git commit -m "feat(tender): add tender service with CRUD, calendar, stats, expiring"
```

---

## Task 3: 后端 Router + main.py

**Files:**
- Create: `backend/app/routers/tender.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create routers/tender.py**

```python
"""
招标管理路由 /api/v1/tender/*
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.tender import TenderCreate, TenderUpdate, UpdateStatusRequest, UpdateFollowerRequest
from app.services.tender_service import tender_service

router = APIRouter()


@router.get("/list", summary="招标列表")
async def list_tenders(
    params: PaginationParams = Depends(get_pagination_params),
    keyword: Optional[str] = Query(default=None),
    tender_method: Optional[str] = Query(default=None),
    info_source: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    follower_id: Optional[int] = Query(default=None),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await tender_service.list_tenders(
        db, params, keyword=keyword, tender_method=tender_method,
        info_source=info_source, status=status, follower_id=follower_id,
        start_date=start_date, end_date=end_date,
    )
    return page_response(items=result["items"], total=result["total"], page=result["page"], page_size=result["page_size"])


@router.post("", summary="创建招标信息")
async def create_tender(
    data: TenderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_service.create_tender(db, data, user_id)
    return success(data=result, message="创建成功")


@router.get("/calendar", summary="日历数据")
async def get_calendar(
    year: int = Query(...),
    month: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await tender_service.get_calendar(db, year, month)
    return success(data=data)


@router.get("/stats", summary="统计概览")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await tender_service.get_stats(db)
    return success(data=data)


@router.get("/expiring", summary="到期提醒")
async def get_expiring(
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await tender_service.get_expiring(db)
    return success(data=data)


@router.get("/{tender_id}", summary="招标详情")
async def get_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await tender_service.get_tender(db, tender_id)
    return success(data=data)


@router.put("/{tender_id}", summary="更新招标信息")
async def update_tender(
    tender_id: int,
    data: TenderUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_service.update_tender(db, tender_id, data, user_id)
    return success(data=result, message="更新成功")


@router.delete("/{tender_id}", summary="删除招标信息")
async def delete_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await tender_service.delete_tender(db, tender_id, user_id)
    return success(message="删除成功")


@router.put("/{tender_id}/status", summary="更新跟进状态")
async def update_status(
    tender_id: int,
    data: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_service.update_status(db, tender_id, data.status, user_id)
    return success(data=result, message="状态更新成功")


@router.put("/{tender_id}/follower", summary="分配跟进人")
async def update_follower(
    tender_id: int,
    data: UpdateFollowerRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_service.update_follower(db, tender_id, data.follower_id, user_id)
    return success(data=result, message="跟进人分配成功")
```

注意：`/calendar`, `/stats`, `/expiring` 路由必须在 `/{tender_id}` 之前声明，否则会被路径参数捕获。

- [ ] **Step 2: Register tender router in main.py**

在 `backend/app/main.py` 中，approval router 注册之后追加：

```python
from app.routers import tender
app.include_router(tender.router, prefix="/api/v1/tender", tags=["招标管理"])
```

- [ ] **Step 3: Delete old DB, test APIs**

```bash
rm -f /Users/wangyunchen/agents/标书系统/backend/data/bid.db
cd /Users/wangyunchen/agents/标书系统/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8002 &
sleep 3

TOKEN=$(curl -s -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# Create tender
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8002/api/v1/tender -d '{"title":"XX市政府采购项目","tender_no":"ZB-2026-001","tender_unit":"XX市财政局","tender_method":"PUBLIC","budget_amount":100.5,"open_bid_time":"2026-04-15T10:00:00","reg_deadline":"2026-04-12T17:00:00","status":"PENDING"}'

# List
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/tender/list?page=1&page_size=20"

# Stats
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/tender/stats

# Calendar
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/tender/calendar?year=2026&month=4"

# Update status
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8002/api/v1/tender/1/status -d '{"status":"DECIDED_BID"}'

kill %1 2>/dev/null || pkill -f "uvicorn app.main:app" 2>/dev/null
```

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add backend/app/routers/tender.py backend/app/main.py
git commit -m "feat(tender): add tender router with 10 APIs"
```

---

## Task 4: 前端类型 + API + Service

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/constants/api.ts`
- Create: `frontend/src/services/tender.ts`

- [ ] **Step 1: Add Tender types**

在 `frontend/src/types/api.ts` 末尾追加：

```typescript

/** 招标信息 */
interface Tender {
  id: number;
  title: string;
  tender_no?: string;
  tender_unit?: string;
  tender_method?: string;
  info_source?: string;
  province?: string;
  city?: string;
  budget_amount?: number;
  deposit_amount?: number;
  deposit_deadline?: string;
  reg_deadline?: string;
  open_bid_time?: string;
  status: string;
  follower_id?: number;
  follower_name?: string;
  remark?: string;
  created_at?: string;
}

/** 日历项 */
interface TenderCalendarItem {
  id: number;
  title: string;
  date: string;
  type: 'reg_deadline' | 'deposit_deadline' | 'open_bid';
  label: string;
}

/** 统计 */
interface TenderStats {
  total: number;
  pending: number;
  decided_bid: number;
  decided_give_up: number;
  composing: number;
  submitted: number;
  opened: number;
}
```

- [ ] **Step 2: Add TENDER_API constants**

```typescript
export const TENDER_API = {
  LIST: `${API_PREFIX}/tender/list`,
  CREATE: `${API_PREFIX}/tender`,
  DETAIL: (id: number) => `${API_PREFIX}/tender/${id}`,
  UPDATE: (id: number) => `${API_PREFIX}/tender/${id}`,
  DELETE: (id: number) => `${API_PREFIX}/tender/${id}`,
  UPDATE_STATUS: (id: number) => `${API_PREFIX}/tender/${id}/status`,
  UPDATE_FOLLOWER: (id: number) => `${API_PREFIX}/tender/${id}/follower`,
  CALENDAR: `${API_PREFIX}/tender/calendar`,
  STATS: `${API_PREFIX}/tender/stats`,
  EXPIRING: `${API_PREFIX}/tender/expiring`,
} as const;
```

- [ ] **Step 3: Create services/tender.ts**

```typescript
import { get, post, put, del } from '@/utils/request';
import { TENDER_API } from '@/constants/api';

export function getTenderList(params?: Record<string, unknown>) {
  return get<PaginatedData<Tender>>(TENDER_API.LIST, params);
}
export function createTender(data: Partial<Tender>) {
  return post<Tender>(TENDER_API.CREATE, data);
}
export function getTender(id: number) {
  return get<Tender>(TENDER_API.DETAIL(id));
}
export function updateTender(id: number, data: Partial<Tender>) {
  return put<Tender>(TENDER_API.UPDATE(id), data);
}
export function deleteTender(id: number) {
  return del(TENDER_API.DELETE(id));
}
export function updateTenderStatus(id: number, status: string) {
  return put<Tender>(TENDER_API.UPDATE_STATUS(id), { status });
}
export function updateTenderFollower(id: number, followerId: number) {
  return put<Tender>(TENDER_API.UPDATE_FOLLOWER(id), { follower_id: followerId });
}
export function getTenderCalendar(year: number, month: number) {
  return get<TenderCalendarItem[]>(TENDER_API.CALENDAR, { year, month });
}
export function getTenderStats() {
  return get<TenderStats>(TENDER_API.STATS);
}
export function getTenderExpiring() {
  return get<Tender[]>(TENDER_API.EXPIRING);
}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/types/api.ts frontend/src/constants/api.ts frontend/src/services/tender.ts
git commit -m "feat(tender): add frontend types, API constants and tender service"
```

---

## Task 5: 前端招标列表页

**Files:**
- Create: `frontend/src/pages/Tender/List/index.tsx`

- [ ] **Step 1: Create TenderList page**

左侧筛选栏 + 右侧表格的标准列表页。状态用彩色 Tag。支持新增按钮跳转到 /tender/create。表格操作列有查看/编辑/删除。

关键实现：
- 筛选条件：keyword(Input), tender_method(Select 字典), info_source(Select 字典), status(Select 字典), follower_id(Select 用户), 时间范围(RangePicker)
- 表格列：项目名称, 招标编号, 招标单位, 招标方式, 预算金额(万元), 开标时间, 状态(Tag), 跟进人, 操作
- 状态颜色：PENDING=blue, DECIDED_BID=green, DECIDED_GIVE_UP=default, COMPOSING=orange, SUBMITTED=purple, OPENED=cyan
- 点击"查看"跳转 /tender/{id}，"编辑"跳转 /tender/{id}?edit=1
- 使用 useDictStore 获取字典下拉选项

- [ ] **Step 2: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/pages/Tender/List/index.tsx
git commit -m "feat(tender): add tender list page with filters"
```

---

## Task 6: 前端招标表单页

**Files:**
- Create: `frontend/src/pages/Tender/Form/index.tsx`

- [ ] **Step 1: Create TenderForm page**

新增和编辑共用，通过 URL params 中的 id 判断。分区表单：基本信息、地区信息、财务信息、时间信息、其他。编辑模式加载已有数据。保存后跳转回列表。

使用 useParams 获取 id，有 id 则为编辑，无则新增。金额用 InputNumber（precision=4）。时间用 DatePicker。招标方式/信息来源用字典 Select。跟进人用用户 Select。

- [ ] **Step 2: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/pages/Tender/Form/index.tsx
git commit -m "feat(tender): add tender create/edit form page"
```

---

## Task 7: 前端日历视图 + 路由菜单

**Files:**
- Create: `frontend/src/pages/Tender/Calendar/index.tsx`
- Modify: `frontend/src/routes.tsx`
- Modify: `frontend/src/layouts/BasicLayout.tsx`

- [ ] **Step 1: Create Calendar page**

使用 Ant Design Calendar 组件。dateCellRender 中渲染当天的事件 Tag（不同颜色区分类型）。点击事件跳转详情。顶部可切换月份。

- [ ] **Step 2: Update routes.tsx**

新增 4 个路由：/tender/list, /tender/create, /tender/:id, /tender/calendar

- [ ] **Step 3: Update BasicLayout.tsx menuItems**

新增招标管理菜单组（在审批中心之前），icon 用 FileSearchOutlined：
```
{ key: '/tender', icon: <FileSearchOutlined />, label: '招标管理', children: [
  { key: '/tender/list', label: '招标列表' },
  { key: '/tender/calendar', label: '日历视图' },
]}
```

- [ ] **Step 4: Verify TS + build, commit**

```bash
cd /Users/wangyunchen/agents/标书系统/frontend && npx tsc --noEmit && npm run build
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/pages/Tender/ frontend/src/routes.tsx frontend/src/layouts/BasicLayout.tsx
git commit -m "feat(tender): add calendar view, routes and menu"
```

---

## Task 8: 端到端验证

验证 10 个 API + 前端构建 + 页面功能。

---

## Verification Checklist

| # | 验收项 |
|---|---|
| 1 | 10 个招标 API 全部可用 |
| 2 | 列表页筛选、分页正常 |
| 3 | 新增/编辑招标信息正常 |
| 4 | 状态更新正常 |
| 5 | 日历视图展示关键日期 |
| 6 | 统计概览数据正确 |
| 7 | 到期提醒返回正确 |
| 8 | TS 编译 + Vite 构建通过 |
