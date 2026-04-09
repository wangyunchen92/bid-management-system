# Phase 1d: 简易审批引擎 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现简易审批流（发起→同意/驳回/转审），含后端 7 个 API 和前端审批中心页面。

**Architecture:** 新建 approval 模块（独立于 system），两张表 approval_instance + approval_record。后端新建 models/approval.py, schemas/approval.py, services/approval_service.py, routers/approval.py。前端新增审批中心页面（Tabs：我的待办/我发起的）。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, Ant Design (Tabs/Table/Modal/Timeline/Tag)

---

## File Map

### Backend

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/approval.py` | Create | ApprovalInstance + ApprovalRecord 模型 |
| `backend/app/schemas/approval.py` | Create | 审批相关 Schema |
| `backend/app/services/approval_service.py` | Create | 审批业务逻辑 |
| `backend/app/routers/approval.py` | Create | /api/v1/approval/* 路由 |
| `backend/app/main.py` | Modify | 注册 approval router |

### Frontend

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/types/api.ts` | Modify | 新增审批类型 |
| `frontend/src/constants/api.ts` | Modify | 新增审批 API 路径 |
| `frontend/src/services/approval.ts` | Create | 审批 API 调用 |
| `frontend/src/pages/Workflow/index.tsx` | Create | 审批中心页 |
| `frontend/src/layouts/BasicLayout.tsx` | Modify | 菜单新增审批中心 |
| `frontend/src/routes.tsx` | Modify | 新增路由 |

---

## Task 1: 后端模型 + Schema

**Files:**
- Create: `backend/app/models/approval.py`
- Create: `backend/app/schemas/approval.py`

- [ ] **Step 1: Create models/approval.py**

```python
"""
审批模型
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base
from app.models.base import BaseModel

_pk_type = Integer if settings.DB_TYPE == "sqlite" else BigInteger


class ApprovalInstance(BaseModel):
    """审批实例"""
    __tablename__ = "approval_instance"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    biz_type: Mapped[str] = mapped_column(String(50), nullable=False)
    biz_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    initiator_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    approver_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    result_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ApprovalRecord(Base):
    """审批记录"""
    __tablename__ = "approval_record"

    id: Mapped[int] = mapped_column(_pk_type, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    operator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
```

- [ ] **Step 2: Create schemas/approval.py**

```python
"""
审批 Schema
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SubmitApprovalRequest(BaseModel):
    title: str = Field(..., max_length=200)
    biz_type: str = Field(..., max_length=50)
    biz_id: Optional[int] = Field(default=None)
    approver_id: int = Field(...)


class ApproveRequest(BaseModel):
    comment: Optional[str] = Field(default=None)


class RejectRequest(BaseModel):
    comment: Optional[str] = Field(default=None)


class TransferRequest(BaseModel):
    to_user_id: int = Field(...)
    comment: Optional[str] = Field(default=None)


class ApprovalInstanceResponse(BaseModel):
    id: int
    title: str
    biz_type: str
    biz_id: Optional[int] = None
    initiator_id: int
    initiator_name: Optional[str] = None
    approver_id: int
    approver_name: Optional[str] = None
    status: str = "PENDING"
    result_comment: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApprovalRecordResponse(BaseModel):
    id: int
    instance_id: int
    operator_id: int
    operator_name: Optional[str] = None
    action: str
    comment: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApprovalDetailResponse(BaseModel):
    instance: ApprovalInstanceResponse
    records: List[ApprovalRecordResponse] = []
```

- [ ] **Step 3: Verify and commit**

```bash
cd /Users/wangyunchen/agents/标书系统/backend && python3 -c "from app.models.approval import ApprovalInstance, ApprovalRecord; print('OK')"
git add backend/app/models/approval.py backend/app/schemas/approval.py
git commit -m "feat(approval): add approval instance/record models and schemas"
```

---

## Task 2: 后端 Service

**Files:**
- Create: `backend/app/services/approval_service.py`

- [ ] **Step 1: Create approval_service.py**

```python
"""
审批服务
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import BusinessException, ForbiddenException, NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.approval import ApprovalInstance, ApprovalRecord
from app.models.system import SysUser
from app.schemas.approval import ApprovalInstanceResponse, ApprovalRecordResponse


class ApprovalService:

    async def _get_user_name(self, db: AsyncSession, user_id: int) -> Optional[str]:
        result = await db.execute(select(SysUser.real_name).where(SysUser.id == user_id))
        return result.scalar_one_or_none()

    async def _instance_to_dict(self, db: AsyncSession, inst: ApprovalInstance) -> dict:
        d = ApprovalInstanceResponse.model_validate(inst).model_dump()
        d["initiator_name"] = await self._get_user_name(db, inst.initiator_id)
        d["approver_name"] = await self._get_user_name(db, inst.approver_id)
        return d

    async def _record_to_dict(self, db: AsyncSession, rec: ApprovalRecord) -> dict:
        d = ApprovalRecordResponse.model_validate(rec).model_dump()
        d["operator_name"] = await self._get_user_name(db, rec.operator_id)
        return d

    async def submit(self, db: AsyncSession, title: str, biz_type: str,
                     biz_id: Optional[int], approver_id: int, initiator_id: int) -> dict:
        # 验证审批人存在
        approver = await db.execute(
            select(SysUser).where(SysUser.id == approver_id, SysUser.is_deleted == 0, SysUser.status == 1)
        )
        if approver.scalar_one_or_none() is None:
            raise BusinessException("审批人不存在或已被禁用")

        if approver_id == initiator_id:
            raise BusinessException("不能审批自己发起的申请")

        instance = ApprovalInstance(
            title=title,
            biz_type=biz_type,
            biz_id=biz_id,
            initiator_id=initiator_id,
            approver_id=approver_id,
            status="PENDING",
        )
        db.add(instance)
        await db.flush()

        record = ApprovalRecord(
            instance_id=instance.id,
            operator_id=initiator_id,
            action="SUBMIT",
            comment=f"发起审批，指定审批人",
        )
        db.add(record)
        await db.flush()
        await db.refresh(instance)

        return await self._instance_to_dict(db, instance)

    async def my_pending(self, db: AsyncSession, user_id: int, params: PaginationParams) -> dict:
        query = select(ApprovalInstance).where(
            ApprovalInstance.approver_id == user_id,
            ApprovalInstance.status == "PENDING",
            ApprovalInstance.is_deleted == 0,
        )
        result = await paginate(db, query, params, sort_column=ApprovalInstance.created_at)
        items = []
        for inst in result["items"]:
            items.append(await self._instance_to_dict(db, inst))
        result["items"] = items
        return result

    async def my_initiated(self, db: AsyncSession, user_id: int, params: PaginationParams) -> dict:
        query = select(ApprovalInstance).where(
            ApprovalInstance.initiator_id == user_id,
            ApprovalInstance.is_deleted == 0,
        )
        result = await paginate(db, query, params, sort_column=ApprovalInstance.created_at)
        items = []
        for inst in result["items"]:
            items.append(await self._instance_to_dict(db, inst))
        result["items"] = items
        return result

    async def get_detail(self, db: AsyncSession, instance_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(ApprovalInstance).where(ApprovalInstance.id == instance_id, ApprovalInstance.is_deleted == 0)
        )
        inst = result.scalar_one_or_none()
        if inst is None:
            raise NotFoundException("审批实例不存在")

        if inst.initiator_id != user_id and inst.approver_id != user_id:
            raise ForbiddenException("无权查看此审批")

        inst_dict = await self._instance_to_dict(db, inst)

        records_result = await db.execute(
            select(ApprovalRecord)
            .where(ApprovalRecord.instance_id == instance_id)
            .order_by(ApprovalRecord.created_at.asc())
        )
        records = [await self._record_to_dict(db, r) for r in records_result.scalars().all()]

        return {"instance": inst_dict, "records": records}

    async def approve(self, db: AsyncSession, instance_id: int, user_id: int, comment: Optional[str]) -> dict:
        inst = await self._get_pending_instance(db, instance_id, user_id)

        inst.status = "APPROVED"
        inst.result_comment = comment
        inst.approved_at = datetime.now(timezone.utc)

        db.add(ApprovalRecord(
            instance_id=inst.id, operator_id=user_id, action="APPROVE", comment=comment,
        ))
        await db.flush()
        await db.refresh(inst)
        return await self._instance_to_dict(db, inst)

    async def reject(self, db: AsyncSession, instance_id: int, user_id: int, comment: Optional[str]) -> dict:
        inst = await self._get_pending_instance(db, instance_id, user_id)

        inst.status = "REJECTED"
        inst.result_comment = comment
        inst.approved_at = datetime.now(timezone.utc)

        db.add(ApprovalRecord(
            instance_id=inst.id, operator_id=user_id, action="REJECT", comment=comment,
        ))
        await db.flush()
        await db.refresh(inst)
        return await self._instance_to_dict(db, inst)

    async def transfer(self, db: AsyncSession, instance_id: int, user_id: int,
                       to_user_id: int, comment: Optional[str]) -> dict:
        inst = await self._get_pending_instance(db, instance_id, user_id)

        # 验证转审人
        to_user = await db.execute(
            select(SysUser).where(SysUser.id == to_user_id, SysUser.is_deleted == 0, SysUser.status == 1)
        )
        if to_user.scalar_one_or_none() is None:
            raise BusinessException("转审人不存在或已被禁用")

        inst.approver_id = to_user_id

        db.add(ApprovalRecord(
            instance_id=inst.id, operator_id=user_id, action="TRANSFER",
            comment=comment or f"转审",
        ))
        await db.flush()
        await db.refresh(inst)
        return await self._instance_to_dict(db, inst)

    async def _get_pending_instance(self, db: AsyncSession, instance_id: int, user_id: int) -> ApprovalInstance:
        result = await db.execute(
            select(ApprovalInstance).where(ApprovalInstance.id == instance_id, ApprovalInstance.is_deleted == 0)
        )
        inst = result.scalar_one_or_none()
        if inst is None:
            raise NotFoundException("审批实例不存在")
        if inst.status != "PENDING":
            raise BusinessException("该审批已处理，不可重复操作")
        if inst.approver_id != user_id:
            raise ForbiddenException("你不是当前审批人")
        return inst


approval_service = ApprovalService()
```

- [ ] **Step 2: Verify and commit**

```bash
cd /Users/wangyunchen/agents/标书系统/backend && python3 -c "from app.services.approval_service import approval_service; print('OK')"
git add backend/app/services/approval_service.py
git commit -m "feat(approval): add approval service with submit/approve/reject/transfer"
```

---

## Task 3: 后端 Router + main.py

**Files:**
- Create: `backend/app/routers/approval.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create routers/approval.py**

```python
"""
审批路由 /api/v1/approval/*
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.approval import SubmitApprovalRequest, ApproveRequest, RejectRequest, TransferRequest
from app.services.approval_service import approval_service

router = APIRouter()


@router.post("/submit", summary="发起审批")
async def submit_approval(
    data: SubmitApprovalRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.submit(
        db, title=data.title, biz_type=data.biz_type,
        biz_id=data.biz_id, approver_id=data.approver_id,
        initiator_id=user_id,
    )
    return success(data=result, message="审批已发起")


@router.get("/my-pending", summary="我的待审批")
async def my_pending(
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.my_pending(db, user_id, params)
    return page_response(
        items=result["items"], total=result["total"],
        page=result["page"], page_size=result["page_size"],
    )


@router.get("/my-initiated", summary="我发起的审批")
async def my_initiated(
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.my_initiated(db, user_id, params)
    return page_response(
        items=result["items"], total=result["total"],
        page=result["page"], page_size=result["page_size"],
    )


@router.get("/{instance_id}", summary="审批详情")
async def get_detail(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.get_detail(db, instance_id, user_id)
    return success(data=result)


@router.post("/{instance_id}/approve", summary="同意")
async def approve(
    instance_id: int,
    data: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.approve(db, instance_id, user_id, data.comment)
    return success(data=result, message="已同意")


@router.post("/{instance_id}/reject", summary="驳回")
async def reject(
    instance_id: int,
    data: RejectRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.reject(db, instance_id, user_id, data.comment)
    return success(data=result, message="已驳回")


@router.post("/{instance_id}/transfer", summary="转审")
async def transfer(
    instance_id: int,
    data: TransferRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.transfer(db, instance_id, user_id, data.to_user_id, data.comment)
    return success(data=result, message="已转审")
```

- [ ] **Step 2: Register approval router in main.py**

在 `backend/app/main.py` 中，在 system router 注册之后追加：

```python
from app.routers import approval
app.include_router(approval.router, prefix="/api/v1/approval", tags=["审批管理"])
```

- [ ] **Step 3: Delete old DB, test APIs**

```bash
rm -f /Users/wangyunchen/agents/标书系统/backend/data/bid.db
cd /Users/wangyunchen/agents/标书系统/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8002 &
sleep 3

# Login as admin
TOKEN=$(curl -s -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# Create another user for testing
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8002/api/v1/system/users -d '{"username":"zhangsan","password":"123456","real_name":"张三","role":"USER"}'

# Login as zhangsan
TOKEN2=$(curl -s -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"zhangsan","password":"123456"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# zhangsan submits approval to admin(id=1)
curl -s -X POST -H "Authorization: Bearer $TOKEN2" -H "Content-Type: application/json" http://localhost:8002/api/v1/approval/submit -d '{"title":"投标决策：XX项目","biz_type":"BID_DECISION","approver_id":1}'

# admin checks pending
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8002/api/v1/approval/my-pending?page=1&page_size=20"

# admin approves
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8002/api/v1/approval/1/approve -d '{"comment":"同意投标"}'

# zhangsan checks initiated
curl -s -H "Authorization: Bearer $TOKEN2" "http://localhost:8002/api/v1/approval/my-initiated?page=1&page_size=20"

kill %1 2>/dev/null || pkill -f "uvicorn app.main:app" 2>/dev/null
```

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add backend/app/routers/approval.py backend/app/main.py
git commit -m "feat(approval): add approval router and register in main"
```

---

## Task 4: 前端类型 + API + Service

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/constants/api.ts`
- Create: `frontend/src/services/approval.ts`

- [ ] **Step 1: Add approval types**

在 `frontend/src/types/api.ts` 末尾追加：

```typescript

/** 审批实例 */
interface ApprovalInstance {
  id: number;
  title: string;
  biz_type: string;
  biz_id?: number;
  initiator_id: number;
  initiator_name?: string;
  approver_id: number;
  approver_name?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  result_comment?: string;
  approved_at?: string;
  created_at?: string;
}

/** 审批记录 */
interface ApprovalRecord {
  id: number;
  instance_id: number;
  operator_id: number;
  operator_name?: string;
  action: 'SUBMIT' | 'APPROVE' | 'REJECT' | 'TRANSFER';
  comment?: string;
  created_at?: string;
}

/** 审批详情 */
interface ApprovalDetail {
  instance: ApprovalInstance;
  records: ApprovalRecord[];
}
```

- [ ] **Step 2: Add approval API constants**

在 `frontend/src/constants/api.ts` 末尾追加：

```typescript

export const APPROVAL_API = {
  SUBMIT: `${API_PREFIX}/approval/submit`,
  MY_PENDING: `${API_PREFIX}/approval/my-pending`,
  MY_INITIATED: `${API_PREFIX}/approval/my-initiated`,
  DETAIL: (id: number) => `${API_PREFIX}/approval/${id}`,
  APPROVE: (id: number) => `${API_PREFIX}/approval/${id}/approve`,
  REJECT: (id: number) => `${API_PREFIX}/approval/${id}/reject`,
  TRANSFER: (id: number) => `${API_PREFIX}/approval/${id}/transfer`,
} as const;
```

- [ ] **Step 3: Create services/approval.ts**

```typescript
import { get, post } from '@/utils/request';
import { APPROVAL_API } from '@/constants/api';

export function submitApproval(data: { title: string; biz_type: string; biz_id?: number; approver_id: number }) {
  return post<ApprovalInstance>(APPROVAL_API.SUBMIT, data);
}

export function getMyPending(params?: Record<string, unknown>) {
  return get<PaginatedData<ApprovalInstance>>(APPROVAL_API.MY_PENDING, params);
}

export function getMyInitiated(params?: Record<string, unknown>) {
  return get<PaginatedData<ApprovalInstance>>(APPROVAL_API.MY_INITIATED, params);
}

export function getApprovalDetail(id: number) {
  return get<ApprovalDetail>(APPROVAL_API.DETAIL(id));
}

export function approveInstance(id: number, comment?: string) {
  return post<ApprovalInstance>(APPROVAL_API.APPROVE(id), { comment });
}

export function rejectInstance(id: number, comment?: string) {
  return post<ApprovalInstance>(APPROVAL_API.REJECT(id), { comment });
}

export function transferInstance(id: number, toUserId: number, comment?: string) {
  return post<ApprovalInstance>(APPROVAL_API.TRANSFER(id), { to_user_id: toUserId, comment });
}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/types/api.ts frontend/src/constants/api.ts frontend/src/services/approval.ts
git commit -m "feat(approval): add frontend types, API constants and approval service"
```

---

## Task 5: 前端审批中心页面

**Files:**
- Create: `frontend/src/pages/Workflow/index.tsx`

- [ ] **Step 1: Create Workflow page**

```tsx
import { useEffect, useState, useCallback } from 'react';
import {
  Card, Tabs, Table, Button, Modal, Form, Input, Tag, Space,
  Timeline, Typography, message, Select,
} from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, SwapOutlined, SendOutlined,
} from '@ant-design/icons';
import {
  getMyPending, getMyInitiated, getApprovalDetail,
  approveInstance, rejectInstance, transferInstance,
} from '@/services/approval';
import { getUserList } from '@/services/system';
import dayjs from 'dayjs';

const { Text } = Typography;
const { TextArea } = Input;

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  PENDING: { color: 'processing', label: '待审批' },
  APPROVED: { color: 'success', label: '已通过' },
  REJECTED: { color: 'error', label: '已驳回' },
};

const ACTION_MAP: Record<string, { color: string; label: string }> = {
  SUBMIT: { color: 'blue', label: '发起审批' },
  APPROVE: { color: 'green', label: '同意' },
  REJECT: { color: 'red', label: '驳回' },
  TRANSFER: { color: 'orange', label: '转审' },
};

export default function WorkflowPage() {
  const [activeTab, setActiveTab] = useState('pending');
  const [pendingList, setPendingList] = useState<ApprovalInstance[]>([]);
  const [initiatedList, setInitiatedList] = useState<ApprovalInstance[]>([]);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [initiatedTotal, setInitiatedTotal] = useState(0);
  const [pendingPage, setPendingPage] = useState(1);
  const [initiatedPage, setInitiatedPage] = useState(1);
  const [loading, setLoading] = useState(false);

  // 审批操作
  const [actionModal, setActionModal] = useState<{ type: 'approve' | 'reject' | 'transfer'; id: number } | null>(null);
  const [actionForm] = Form.useForm();
  const [users, setUsers] = useState<{ value: number; label: string }[]>([]);

  // 详情
  const [detailModal, setDetailModal] = useState(false);
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);

  const loadPending = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getMyPending({ page: pendingPage, page_size: 20 });
      setPendingList(res.data.items);
      setPendingTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [pendingPage]);

  const loadInitiated = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getMyInitiated({ page: initiatedPage, page_size: 20 });
      setInitiatedList(res.data.items);
      setInitiatedTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  }, [initiatedPage]);

  useEffect(() => {
    if (activeTab === 'pending') loadPending();
    else loadInitiated();
  }, [activeTab, loadPending, loadInitiated]);

  const loadUsers = useCallback(async () => {
    const res = await getUserList({ page: 1, page_size: 100 });
    setUsers(res.data.items.map((u: SystemUser) => ({ value: u.id, label: u.real_name })));
  }, []);

  const handleAction = (type: 'approve' | 'reject' | 'transfer', id: number) => {
    actionForm.resetFields();
    if (type === 'transfer') loadUsers();
    setActionModal({ type, id });
  };

  const handleActionSubmit = async () => {
    if (!actionModal) return;
    const values = await actionForm.validateFields();
    const { type, id } = actionModal;

    if (type === 'approve') {
      await approveInstance(id, values.comment);
      message.success('已同意');
    } else if (type === 'reject') {
      await rejectInstance(id, values.comment);
      message.success('已驳回');
    } else {
      await transferInstance(id, values.to_user_id, values.comment);
      message.success('已转审');
    }
    setActionModal(null);
    loadPending();
    loadInitiated();
  };

  const handleViewDetail = async (id: number) => {
    try {
      const res = await getApprovalDetail(id);
      setDetail(res.data);
      setDetailModal(true);
    } catch { /* handled */ }
  };

  const pendingColumns = [
    { title: '标题', dataIndex: 'title', key: 'title',
      render: (v: string, r: ApprovalInstance) => <a onClick={() => handleViewDetail(r.id)}>{v}</a>,
    },
    { title: '发起人', dataIndex: 'initiator_name', key: 'initiator_name', width: 100 },
    { title: '发起时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '操作', key: 'action', width: 200,
      render: (_: unknown, r: ApprovalInstance) => (
        <Space>
          <Button type="primary" size="small" icon={<CheckCircleOutlined />} onClick={() => handleAction('approve', r.id)}>同意</Button>
          <Button danger size="small" icon={<CloseCircleOutlined />} onClick={() => handleAction('reject', r.id)}>驳回</Button>
          <Button size="small" icon={<SwapOutlined />} onClick={() => handleAction('transfer', r.id)}>转审</Button>
        </Space>
      ),
    },
  ];

  const initiatedColumns = [
    { title: '标题', dataIndex: 'title', key: 'title',
      render: (v: string, r: ApprovalInstance) => <a onClick={() => handleViewDetail(r.id)}>{v}</a>,
    },
    { title: '审批人', dataIndex: 'approver_name', key: 'approver_name', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => {
        const s = STATUS_MAP[v] || { color: 'default', label: v };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    { title: '发起时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
  ];

  return (
    <Card>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'pending',
          label: `我的待办 (${pendingTotal})`,
          children: (
            <Table dataSource={pendingList} columns={pendingColumns} rowKey="id" loading={loading} size="middle"
              pagination={{ current: pendingPage, total: pendingTotal, pageSize: 20, onChange: setPendingPage }} />
          ),
        },
        {
          key: 'initiated',
          label: '我发起的',
          children: (
            <Table dataSource={initiatedList} columns={initiatedColumns} rowKey="id" loading={loading} size="middle"
              pagination={{ current: initiatedPage, total: initiatedTotal, pageSize: 20, onChange: setInitiatedPage }} />
          ),
        },
      ]} />

      {/* 审批操作弹窗 */}
      <Modal
        title={actionModal?.type === 'approve' ? '同意审批' : actionModal?.type === 'reject' ? '驳回审批' : '转审'}
        open={!!actionModal}
        onCancel={() => setActionModal(null)}
        onOk={handleActionSubmit}
        destroyOnClose
      >
        <Form form={actionForm} layout="vertical" style={{ marginTop: 16 }}>
          {actionModal?.type === 'transfer' && (
            <Form.Item name="to_user_id" label="转审人" rules={[{ required: true, message: '请选择转审人' }]}>
              <Select placeholder="选择转审人" options={users} showSearch optionFilterProp="label" />
            </Form.Item>
          )}
          <Form.Item name="comment" label="审批意见">
            <TextArea rows={3} placeholder="请输入审批意见（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 审批详情弹窗 */}
      <Modal
        title="审批详情"
        open={detailModal}
        onCancel={() => setDetailModal(false)}
        footer={null}
        width={600}
      >
        {detail && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ fontSize: 16 }}>{detail.instance.title}</Text>
              <Tag color={STATUS_MAP[detail.instance.status]?.color} style={{ marginLeft: 8 }}>
                {STATUS_MAP[detail.instance.status]?.label}
              </Tag>
            </div>
            <Timeline
              items={detail.records.map((r) => ({
                color: ACTION_MAP[r.action]?.color || 'gray',
                children: (
                  <div>
                    <Space>
                      <Tag color={ACTION_MAP[r.action]?.color}>{ACTION_MAP[r.action]?.label}</Tag>
                      <Text strong>{r.operator_name}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {r.created_at ? dayjs(r.created_at).format('YYYY-MM-DD HH:mm') : ''}
                      </Text>
                    </Space>
                    {r.comment && <div style={{ marginTop: 4, color: '#475569' }}>{r.comment}</div>}
                  </div>
                ),
              }))}
            />
          </div>
        )}
      </Modal>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/pages/Workflow/index.tsx
git commit -m "feat(approval): add workflow center page with pending/initiated tabs"
```

---

## Task 6: 前端路由和菜单

**Files:**
- Modify: `frontend/src/routes.tsx`
- Modify: `frontend/src/layouts/BasicLayout.tsx`

- [ ] **Step 1: Update routes.tsx**

添加 Workflow lazy import 和路由：

```tsx
const Workflow = lazy(() => import('@/pages/Workflow'));
```

在 BasicLayout routes 中追加：
```tsx
<Route path="/workflow" element={<Workflow />} />
```

- [ ] **Step 2: Update BasicLayout.tsx**

在 icon import 中添加 `AuditOutlined`。

在 menuItems 中，在仪表盘之后、系统管理之前插入：
```tsx
{ key: '/workflow', icon: <AuditOutlined />, label: '审批中心' },
```

- [ ] **Step 3: Verify and commit**

```bash
cd /Users/wangyunchen/agents/标书系统/frontend && npx tsc --noEmit && npm run build
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/routes.tsx frontend/src/layouts/BasicLayout.tsx
git commit -m "feat(approval): add workflow route and menu"
```

---

## Task 7: 端到端验证

测试完整审批流程：发起→同意/驳回/转审，前端构建。

---

## Verification Checklist

| # | 验收项 |
|---|---|
| 1 | 7 个审批 API 全部可用 |
| 2 | 发起审批 → 审批人待办可见 |
| 3 | 同意 → 状态变 APPROVED |
| 4 | 驳回 → 状态变 REJECTED |
| 5 | 转审 → 换审批人 |
| 6 | 非审批人操作被拒绝 |
| 7 | 审批详情含完整记录 |
| 8 | 前端审批中心 Tab 正常 |
| 9 | TS 编译 + Vite 构建通过 |
