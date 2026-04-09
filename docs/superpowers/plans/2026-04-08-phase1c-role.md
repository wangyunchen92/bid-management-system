# Phase 1c: 权限系统（角色管理）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现角色 CRUD、用户角色分配、用户信息返回角色列表，含前端角色管理页和用户页改造。

**Architecture:** 新增 SysRole + SysUserRole 两张表。角色为简单列表（非树形）。用户与角色多对多。auth_service 的 /me 接口增强返回 roles。前端新增角色管理页，改造用户管理页支持多角色。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, Ant Design (Table/Modal/Form/Select)

---

## File Map

### Backend

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/system.py` | Modify | 新增 SysRole, SysUserRole |
| `backend/app/schemas/system.py` | Modify | 新增角色 Schema + AssignRolesRequest |
| `backend/app/services/system_service.py` | Modify | 新增角色 CRUD + 用户角色分配 + list_users 返回 roles |
| `backend/app/services/auth_service.py` | Modify | get_current_user_info 返回 roles 数组 |
| `backend/app/routers/system.py` | Modify | 新增 6 个路由 |
| `backend/app/main.py` | Modify | 初始化 3 个预置角色 + admin 关联 |

### Frontend

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/types/api.ts` | Modify | 新增 SysRole，SystemUser 加 roles |
| `frontend/src/constants/api.ts` | Modify | 新增角色 API 路径 |
| `frontend/src/services/system.ts` | Modify | 新增角色 API 调用 |
| `frontend/src/pages/System/Role/index.tsx` | Create | 角色管理页 |
| `frontend/src/pages/System/User/index.tsx` | Modify | 多角色显示和选择 |
| `frontend/src/layouts/BasicLayout.tsx` | Modify | 菜单新增角色管理 |
| `frontend/src/routes.tsx` | Modify | 新增路由 |

---

## Task 1: 后端模型和 Schema

**Files:**
- Modify: `backend/app/models/system.py`
- Modify: `backend/app/schemas/system.py`

- [ ] **Step 1: Add SysRole and SysUserRole to models/system.py**

在 `backend/app/models/system.py` 中，SysDepartment 之后、SysDictType 之前插入：

```python
class SysRole(BaseModel):
    """角色表"""
    __tablename__ = "sys_role"

    role_name: Mapped[str] = mapped_column(String(50), nullable=False)
    role_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")


class SysUserRole(Base):
    """用户角色关联表"""
    __tablename__ = "sys_user_role"

    id: Mapped[int] = mapped_column(_pk_type, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
```

- [ ] **Step 2: Add role schemas to schemas/system.py**

在 `backend/app/schemas/system.py` 末尾追加：

```python
# ========== 角色 ==========

class RoleCreate(BaseModel):
    role_name: str = Field(..., max_length=50)
    role_code: str = Field(..., max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = Field(default=0)
    status: int = Field(default=1)


class RoleUpdate(BaseModel):
    role_name: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: Optional[int] = Field(default=None)
    status: Optional[int] = Field(default=None)


class RoleResponse(BaseModel):
    id: int
    role_name: str
    role_code: str
    description: Optional[str] = None
    sort_order: int = 0
    status: int = 1
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AssignRolesRequest(BaseModel):
    role_ids: List[int] = Field(default_factory=list)
```

- [ ] **Step 3: Verify and commit**

```bash
cd /Users/wangyunchen/agents/标书系统/backend && python3 -c "from app.models.system import SysRole, SysUserRole; print('OK')"
cd /Users/wangyunchen/agents/标书系统 && git add backend/app/models/system.py backend/app/schemas/system.py
git commit -m "feat(role): add SysRole/SysUserRole models and role schemas"
```

---

## Task 2: 后端 Service + auth_service 改造

**Files:**
- Modify: `backend/app/services/system_service.py`
- Modify: `backend/app/services/auth_service.py`

- [ ] **Step 1: Add role methods and update list_users in system_service.py**

顶部 import 补充（在已有 import 基础上追加）：
```python
from app.models.system import SysDictItem, SysDictType, SysDepartment, SysUser, SysRole, SysUserRole
from app.schemas.system import (
    ...,  # 已有的
    RoleCreate, RoleUpdate, RoleResponse,
)
```

在 SystemService 类末尾追加角色方法：

```python
    # ================================================================== #
    #  角色管理
    # ================================================================== #

    async def list_roles(self, db: AsyncSession) -> List[dict]:
        result = await db.execute(
            select(SysRole)
            .where(SysRole.is_deleted == 0)
            .order_by(SysRole.sort_order.asc(), SysRole.id.asc())
        )
        return [RoleResponse.model_validate(r).model_dump() for r in result.scalars().all()]

    async def create_role(self, db: AsyncSession, data: RoleCreate, user_id: int) -> dict:
        existing = await db.execute(
            select(SysRole).where(SysRole.role_code == data.role_code, SysRole.is_deleted == 0)
        )
        if existing.scalar_one_or_none():
            raise DuplicateException(f"角色编码 '{data.role_code}' 已存在")

        role = SysRole(**data.model_dump(), created_by=user_id, updated_by=user_id)
        db.add(role)
        await db.flush()
        await db.refresh(role)
        return RoleResponse.model_validate(role).model_dump()

    async def update_role(self, db: AsyncSession, role_id: int, data: RoleUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(SysRole).where(SysRole.id == role_id, SysRole.is_deleted == 0)
        )
        role = result.scalar_one_or_none()
        if role is None:
            raise NotFoundException("角色不存在")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(role, key, value)
        await db.flush()
        await db.refresh(role)
        return RoleResponse.model_validate(role).model_dump()

    async def delete_role(self, db: AsyncSession, role_id: int, user_id: int) -> None:
        result = await db.execute(
            select(SysRole).where(SysRole.id == role_id, SysRole.is_deleted == 0)
        )
        role = result.scalar_one_or_none()
        if role is None:
            raise NotFoundException("角色不存在")
        if role.role_code == "SUPER_ADMIN":
            raise BusinessException("预置角色不可删除")

        user_count = await db.execute(
            select(SysUserRole).where(SysUserRole.role_id == role_id).limit(1)
        )
        if user_count.scalar_one_or_none():
            raise BusinessException("该角色下存在关联用户，请先移除")

        role.is_deleted = 1
        role.updated_by = user_id
        await db.flush()

    async def get_user_roles(self, db: AsyncSession, user_id: int) -> List[dict]:
        result = await db.execute(
            select(SysRole.id, SysRole.role_name, SysRole.role_code)
            .join(SysUserRole, SysRole.id == SysUserRole.role_id)
            .where(SysUserRole.user_id == user_id, SysRole.is_deleted == 0, SysRole.status == 1)
        )
        return [{"role_id": r[0], "role_name": r[1], "role_code": r[2]} for r in result.all()]

    async def assign_user_roles(self, db: AsyncSession, user_id: int, role_ids: List[int], current_user_id: int) -> List[dict]:
        # 验证用户存在
        user_result = await db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        if user_result.scalar_one_or_none() is None:
            raise NotFoundException("用户不存在")

        # 先删后增
        from sqlalchemy import delete
        await db.execute(delete(SysUserRole).where(SysUserRole.user_id == user_id))

        for role_id in role_ids:
            role_result = await db.execute(
                select(SysRole).where(SysRole.id == role_id, SysRole.is_deleted == 0)
            )
            if role_result.scalar_one_or_none() is None:
                raise BusinessException(f"角色 ID {role_id} 不存在")
            db.add(SysUserRole(user_id=user_id, role_id=role_id))

        await db.flush()
        return await self.get_user_roles(db, user_id)
```

同时修改 `list_users` 方法：在构建每个 user_dict 后追加 roles 信息。找到 `list_users` 方法中 `items.append(user_dict)` 之前，追加：

```python
            # 获取用户角色
            role_result = await db.execute(
                select(SysRole.id, SysRole.role_name, SysRole.role_code)
                .join(SysUserRole, SysRole.id == SysUserRole.role_id)
                .where(SysUserRole.user_id == user.id, SysRole.is_deleted == 0)
            )
            user_dict["roles"] = [{"role_id": r[0], "role_name": r[1], "role_code": r[2]} for r in role_result.all()]
```

同样修改 `create_user` 和 `update_user` 方法，在返回 user_dict 前追加相同的角色查询。

- [ ] **Step 2: Modify auth_service.py — get_current_user_info returns roles**

在 `backend/app/services/auth_service.py` 的 `get_current_user_info` 方法中，在返回 dict 前查询用户角色。

在方法内、`return` 语句之前追加：

```python
        from app.models.system import SysRole, SysUserRole
        role_result = await db.execute(
            select(SysRole.id, SysRole.role_name, SysRole.role_code)
            .join(SysUserRole, SysRole.id == SysUserRole.role_id)
            .where(SysUserRole.user_id == user_id, SysRole.is_deleted == 0)
        )
        roles = [{"role_id": r[0], "role_name": r[1], "role_code": r[2]} for r in role_result.all()]
```

并在返回 dict 中加入 `"roles": roles`。

- [ ] **Step 3: Verify and commit**

```bash
cd /Users/wangyunchen/agents/标书系统/backend && python3 -c "from app.services.system_service import system_service; print('OK')"
cd /Users/wangyunchen/agents/标书系统 && git add backend/app/services/system_service.py backend/app/services/auth_service.py
git commit -m "feat(role): add role CRUD, user-role assignment, and roles in user info"
```

---

## Task 3: 后端 Router + main.py 初始化

**Files:**
- Modify: `backend/app/routers/system.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add role routes to routers/system.py**

顶部 import 补充：
```python
from app.schemas.system import (
    ...,  # 已有的
    RoleCreate, RoleUpdate, AssignRolesRequest,
)
```

在文件末尾追加：

```python
# ================================================================== #
#  角色管理
# ================================================================== #

@router.get("/roles", summary="角色列表")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await system_service.list_roles(db)
    return success(data=data)


@router.post("/roles", summary="创建角色")
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    role = await system_service.create_role(db, data, user_id)
    return success(data=role, message="创建成功")


@router.put("/roles/{role_id}", summary="更新角色")
async def update_role(
    role_id: int,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    role = await system_service.update_role(db, role_id, data, user_id)
    return success(data=role, message="更新成功")


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.delete_role(db, role_id, user_id)
    return success(message="删除成功")


@router.get("/users/{target_user_id}/roles", summary="获取用户角色")
async def get_user_roles(
    target_user_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await system_service.get_user_roles(db, target_user_id)
    return success(data=data)


@router.put("/users/{target_user_id}/roles", summary="分配用户角色")
async def assign_user_roles(
    target_user_id: int,
    data: AssignRolesRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    roles = await system_service.assign_user_roles(db, target_user_id, data.role_ids, user_id)
    return success(data=roles, message="角色分配成功")
```

- [ ] **Step 2: Modify main.py — initialize roles**

在 `_init_base_data` 中，默认部门创建之后、字典初始化之前，添加角色初始化：

```python
        # 初始化角色
        from app.models.system import SysRole, SysUserRole
        role_result = await session.execute(select(SysRole).limit(1))
        if not role_result.scalar_one_or_none():
            roles_data = [
                ("超级管理员", "SUPER_ADMIN", "拥有全部权限", 0),
                ("管理员", "ADMIN", "日常管理操作", 1),
                ("普通用户", "USER", "基础查看操作", 2),
            ]
            role_map = {}
            for name, code, desc, sort in roles_data:
                role = SysRole(role_name=name, role_code=code, description=desc, sort_order=sort, status=1)
                session.add(role)
                await session.flush()
                role_map[code] = role.id

            # admin 关联 SUPER_ADMIN
            admin_result = await session.execute(
                select(SysUser).where(SysUser.username == "admin")
            )
            admin_user = admin_result.scalar_one_or_none()
            if admin_user and "SUPER_ADMIN" in role_map:
                session.add(SysUserRole(user_id=admin_user.id, role_id=role_map["SUPER_ADMIN"]))

            await session.commit()
            logger.info("预置角色已创建，admin 已关联 SUPER_ADMIN")
```

- [ ] **Step 3: Delete old DB, test all APIs**

```bash
rm -f /Users/wangyunchen/agents/标书系统/backend/data/bid.db
cd /Users/wangyunchen/agents/标书系统/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8002 &
sleep 3

TOKEN=$(curl -s -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# 1. Role list (should have 3)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/system/roles | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'Roles: {len(d)}')"

# 2. /me should have roles
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/auth/me | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'User roles: {d.get(\"roles\")}')"

# 3. Get user roles
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/system/users/1/roles | python3 -c "import sys,json; print(json.load(sys.stdin)['data'])"

# 4. Create role
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8002/api/v1/system/roles -d '{"role_name":"测试角色","role_code":"TEST"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 5. Delete SUPER_ADMIN (should fail)
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8002/api/v1/system/roles/1 | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 6. Delete role with user (SUPER_ADMIN has admin, should fail)
# Already tested above

# 7. Assign roles to user
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" http://localhost:8002/api/v1/system/users/1/roles -d '{"role_ids":[1,2]}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

kill %1 2>/dev/null || pkill -f "uvicorn app.main:app" 2>/dev/null
```

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add backend/app/routers/system.py backend/app/main.py
git commit -m "feat(role): add role routes and initialize preset roles"
```

---

## Task 4: 前端类型、API、Service

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/constants/api.ts`
- Modify: `frontend/src/services/system.ts`

- [ ] **Step 1: Add SysRole type and update SystemUser**

在 `frontend/src/types/api.ts` 末尾追加：

```typescript

/** 角色 */
interface SysRole {
  id: number;
  role_name: string;
  role_code: string;
  description?: string;
  sort_order: number;
  status: number;
  created_at?: string;
}

/** 用户角色信息 */
interface UserRoleInfo {
  role_id: number;
  role_name: string;
  role_code: string;
}
```

同时修改 `SystemUser` 接口，追加 `roles` 字段：

```typescript
  roles?: UserRoleInfo[];
```

- [ ] **Step 2: Add role API constants**

在 `frontend/src/constants/api.ts` 的 SYSTEM_API 对象末尾追加：

```typescript
  // 角色
  ROLE_LIST: `${API_PREFIX}/system/roles`,
  ROLE_CREATE: `${API_PREFIX}/system/roles`,
  ROLE_UPDATE: (id: number) => `${API_PREFIX}/system/roles/${id}`,
  ROLE_DELETE: (id: number) => `${API_PREFIX}/system/roles/${id}`,
  USER_ROLES: (id: number) => `${API_PREFIX}/system/users/${id}/roles`,
  ASSIGN_ROLES: (id: number) => `${API_PREFIX}/system/users/${id}/roles`,
```

- [ ] **Step 3: Add role service functions**

在 `frontend/src/services/system.ts` 末尾追加：

```typescript

// ========== 角色 ==========

export function getRoleList() {
  return get<SysRole[]>(SYSTEM_API.ROLE_LIST);
}

export function createRole(data: Partial<SysRole>) {
  return post<SysRole>(SYSTEM_API.ROLE_CREATE, data);
}

export function updateRole(id: number, data: Partial<SysRole>) {
  return put<SysRole>(SYSTEM_API.ROLE_UPDATE(id), data);
}

export function deleteRole(id: number) {
  return del(SYSTEM_API.ROLE_DELETE(id));
}

export function getUserRoles(userId: number) {
  return get<UserRoleInfo[]>(SYSTEM_API.USER_ROLES(userId));
}

export function assignUserRoles(userId: number, roleIds: number[]) {
  return put<UserRoleInfo[]>(SYSTEM_API.ASSIGN_ROLES(userId), { role_ids: roleIds });
}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/types/api.ts frontend/src/constants/api.ts frontend/src/services/system.ts
git commit -m "feat(role): add frontend types, API constants and role service"
```

---

## Task 5: 前端角色管理页

**Files:**
- Create: `frontend/src/pages/System/Role/index.tsx`

- [ ] **Step 1: Create Role page**

Write `frontend/src/pages/System/Role/index.tsx`:

```tsx
import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, InputNumber, Switch,
  Space, Tag, message, Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { getRoleList, createRole, updateRole, deleteRole } from '@/services/system';

export default function RolePage() {
  const [roles, setRoles] = useState<SysRole[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<SysRole | null>(null);
  const [form] = Form.useForm();

  const loadRoles = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getRoleList();
      setRoles(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadRoles(); }, [loadRoles]);

  const handleCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ status: true, sort_order: 0 });
    setModalOpen(true);
  };

  const handleEdit = (role: SysRole) => {
    setEditing(role);
    form.setFieldsValue({ ...role, status: role.status === 1 });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const data = { ...values, status: values.status ? 1 : 0 };
    if (editing) {
      await updateRole(editing.id, data);
      message.success('更新成功');
    } else {
      await createRole(data);
      message.success('创建成功');
    }
    setModalOpen(false);
    loadRoles();
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteRole(id);
      message.success('删除成功');
      loadRoles();
    } catch { /* handled */ }
  };

  const columns = [
    { title: '角色名称', dataIndex: 'role_name', key: 'role_name' },
    {
      title: '角色编码', dataIndex: 'role_code', key: 'role_code',
      render: (v: string) => <code style={{ background: '#f1f5f9', padding: '2px 8px', borderRadius: 4, fontSize: 13 }}>{v}</code>,
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80, align: 'center' as const },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: number) => v === 1 ? <Tag color="success">启用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: unknown, record: SysRole) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          {record.role_code !== 'SUPER_ADMIN' && (
            <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title="角色管理"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新增角色</Button>}
    >
      <Table dataSource={roles} columns={columns} rowKey="id" loading={loading} pagination={false} size="middle" />

      <Modal
        title={editing ? '编辑角色' : '新增角色'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="role_name" label="角色名称" rules={[{ required: true, message: '请输入角色名称' }]}>
            <Input placeholder="如：投标专员" />
          </Form.Item>
          <Form.Item name="role_code" label="角色编码" rules={[{ required: true, message: '请输入角色编码' }]}>
            <Input placeholder="如：BID_SPECIALIST" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="角色职责描述" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序号">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/pages/System/Role/index.tsx
git commit -m "feat(role): add role management page"
```

---

## Task 6: 前端用户页改造 + 路由菜单

**Files:**
- Modify: `frontend/src/pages/System/User/index.tsx`
- Modify: `frontend/src/routes.tsx`
- Modify: `frontend/src/layouts/BasicLayout.tsx`

- [ ] **Step 1: Update User page for multi-role**

在 `frontend/src/pages/System/User/index.tsx` 中需要做以下修改：

1. 导入 `getRoleList` 和 `assignUserRoles`：
```tsx
import {
  getDepartmentTree, getUserList, createUser, updateUser, deleteUser, resetUserPassword,
  getRoleList, assignUserRoles,
} from '@/services/system';
```

2. 新增角色列表 state：
```tsx
const [roleOptions, setRoleOptions] = useState<SysRole[]>([]);
```

3. 在 loadDeptTree 的 useEffect 中同时加载角色：
```tsx
const loadRoles = useCallback(async () => {
  const res = await getRoleList();
  setRoleOptions(res.data);
}, []);

useEffect(() => { loadDeptTree(); loadRoles(); }, [loadDeptTree, loadRoles]);
```

4. 修改表格 columns 中的"角色"列（从单个 Tag 改为多个 Tag）：
```tsx
{ title: '角色', dataIndex: 'roles', key: 'roles', width: 160,
  render: (roles: UserRoleInfo[]) => roles?.length > 0
    ? roles.map((r) => (
        <Tag key={r.role_id} color={r.role_code === 'SUPER_ADMIN' ? 'red' : 'blue'}>
          {r.role_name}
        </Tag>
      ))
    : <Tag>无角色</Tag>,
},
```

删除原来的单角色列（`role` 字段的列）。

5. 修改用户表单中的角色字段（从 Select 单选改为 Select multiple）：
```tsx
<Form.Item name="role_ids" label="角色">
  <Select
    mode="multiple"
    placeholder="选择角色"
    options={roleOptions.map((r) => ({ label: r.role_name, value: r.id }))}
  />
</Form.Item>
```

删除原来的单角色 Select（`role` 字段）。

6. 修改 handleEdit 设置角色 ID 列表：
```tsx
const handleEdit = (user: SystemUser) => {
  setEditing(user);
  form.setFieldsValue({
    ...user,
    role_ids: user.roles?.map((r) => r.role_id) || [],
  });
  setModalOpen(true);
};
```

7. 修改 handleSubmit 在创建/更新后分配角色：
```tsx
const handleSubmit = async () => {
  const values = await form.validateFields();
  const { role_ids, ...userData } = values;
  if (editing) {
    const { username: _u, password: _p, ...updateData } = userData;
    await updateUser(editing.id, updateData);
    if (role_ids !== undefined) {
      await assignUserRoles(editing.id, role_ids);
    }
    message.success('更新成功');
  } else {
    const res = await createUser(userData);
    if (role_ids?.length > 0 && res.data?.id) {
      await assignUserRoles(res.data.id, role_ids);
    }
    message.success('创建成功');
  }
  setModalOpen(false);
  loadUsers();
};
```

- [ ] **Step 2: Update routes.tsx**

添加 Role lazy import 和路由：

```tsx
const Role = lazy(() => import('@/pages/System/Role'));
```

在 BasicLayout 的 routes 中追加：
```tsx
<Route path="/system/role" element={<Role />} />
```

- [ ] **Step 3: Update BasicLayout.tsx menuItems**

在 icon import 中添加 `SafetyCertificateOutlined`。

在 menuItems 的系统管理 children 中，在"用户管理"后面追加：
```tsx
{ key: '/system/role', icon: <SafetyCertificateOutlined />, label: '角色管理' },
```

- [ ] **Step 4: Verify and commit**

```bash
cd /Users/wangyunchen/agents/标书系统/frontend && npx tsc --noEmit && npm run build
cd /Users/wangyunchen/agents/标书系统 && git add frontend/src/pages/System/User/index.tsx frontend/src/pages/System/Role/index.tsx frontend/src/routes.tsx frontend/src/layouts/BasicLayout.tsx
git commit -m "feat(role): update user page for multi-role, add role route and menu"
```

---

## Task 7: 端到端验证

**Files:** None (verification only)

- [ ] **Step 1: Start backend, run API tests**

```bash
rm -f /Users/wangyunchen/agents/标书系统/backend/data/bid.db
cd /Users/wangyunchen/agents/标书系统/backend && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8002 &
sleep 3

TOKEN=$(curl -s -X POST http://localhost:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

# 1. Roles list (3 preset)
# 2. /me returns roles
# 3. Create role
# 4. Duplicate role code (should fail)
# 5. Delete SUPER_ADMIN (should fail - preset)
# 6. Assign roles
# 7. Get user roles
# 8. Delete role with user (should fail)
# 9. Frontend: tsc + build
```

- [ ] **Step 2: Cleanup**

```bash
kill %1 2>/dev/null || pkill -f "uvicorn app.main:app" 2>/dev/null
```

---

## Verification Checklist

| # | 验收项 |
|---|---|
| 1 | 3 个预置角色自动创建 |
| 2 | admin 关联 SUPER_ADMIN |
| 3 | /me 返回 roles 数组 |
| 4 | 角色 CRUD 4 个 API 正常 |
| 5 | 用户角色分配 2 个 API 正常 |
| 6 | 预置角色不可删除 |
| 7 | 有用户的角色不可删除 |
| 8 | 前端角色管理页正常 |
| 9 | 用户页显示多角色、可多选 |
| 10 | TS 编译 + Vite 构建通过 |
