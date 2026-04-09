# Phase 1c 设计：权限系统（角色管理）

> 日期：2026-04-08
> 状态：已确认

## 简化策略

ERP 有完整 RBAC（4 张表）。标书系统简化为角色+用户角色关联，不做菜单表和权限码。用角色编码直接控制访问，后续需要细粒度权限时再扩展。

## 数据模型

### sys_role（新建）

继承 BaseModel（含 AuditMixin）。

| 字段 | 类型 | 说明 |
|---|---|---|
| role_name | VARCHAR(50) NOT NULL | 角色名称 |
| role_code | VARCHAR(50) UNIQUE NOT NULL | 角色编码，不可改 |
| description | VARCHAR(255) | 描述 |
| sort_order | INTEGER default 0 | 排序 |
| status | TINYINT default 1 | 启用/停用 |

### sys_user_role（新建）

直接继承 Base，无 is_deleted（物理删除）。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| user_id | BIGINT NOT NULL | 用户 ID |
| role_id | BIGINT NOT NULL | 角色 ID |
| created_at | DATETIME | 创建时间 |

## API 接口

### 角色 CRUD（4 个）

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/system/roles` | 角色列表（全量，不分页） | 登录 |
| POST | `/api/v1/system/roles` | 创建角色 | SUPER_ADMIN |
| PUT | `/api/v1/system/roles/{id}` | 更新角色（不可改 code） | SUPER_ADMIN |
| DELETE | `/api/v1/system/roles/{id}` | 删除角色 | SUPER_ADMIN |

### 用户角色分配（2 个）

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/system/users/{id}/roles` | 获取用户的角色列表 | 登录 |
| PUT | `/api/v1/system/users/{id}/roles` | 分配角色（先删后增） | SUPER_ADMIN |

### 删除保护

- 删除角色前检查是否有关联用户，有则拒绝
- 预置角色（SUPER_ADMIN）不可删除

### 用户信息增强

GET /api/v1/auth/me 和 GET /api/v1/system/users 返回的用户信息中增加 roles 数组。

## 前端

### 路由

| 路由 | 页面 |
|---|---|
| `/system/role` | 角色管理 |

### 侧边栏菜单

```
系统管理
  ├── 组织架构
  ├── 用户管理
  ├── 角色管理
  └── 数据字典
```

### 角色管理页（/system/role）

标准 Table + Modal CRUD：
- 表格列：角色名称、角色编码、描述、排序、状态、操作
- 新增/编辑弹窗：角色名称*、角色编码*（编辑时 disabled）、描述、排序号、状态

### 用户管理页改造

- 用户表格"角色"列：从单个 Tag 改为多个 Tag（显示所有角色名）
- 编辑用户弹窗：角色字段从 Select 单选改为 Select multiple（多角色选择）

### 前端类型

```typescript
interface SysRole {
  id: number;
  role_name: string;
  role_code: string;
  description?: string;
  sort_order: number;
  status: number;
}
```

UserResponse 和 SystemUser 增加 roles 字段：
```typescript
roles: { role_id: number; role_name: string; role_code: string }[]
```

## 初始化数据

启动时创建 3 个预置角色：
- SUPER_ADMIN / 超级管理员 / 拥有全部权限
- ADMIN / 管理员 / 日常管理操作
- USER / 普通用户 / 基础查看操作

admin 用户通过 sys_user_role 关联 SUPER_ADMIN 角色。

## 验收标准

1. 角色 CRUD 4 个 API 正常
2. 用户角色分配 2 个 API 正常
3. 预置 3 个角色自动创建
4. admin 关联 SUPER_ADMIN 角色
5. 删除有用户的角色被拒绝
6. 前端角色管理页正常
7. 用户管理页显示多角色、可多选角色
8. TypeScript 编译无错误
9. Vite 构建成功
