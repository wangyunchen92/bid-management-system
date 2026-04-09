# Phase 1b 设计：组织架构模块

> 日期：2026-04-08
> 状态：已确认

## 背景

组织架构是权限系统和审批引擎的前置依赖。从 ERP 复用，简化为一对多（用户属于一个部门），去掉多租户。

## 简化决策

| ERP | 标书系统 | 理由 |
|---|---|---|
| 多对多（SysUserDept 中间表）| 一对多（user.dept_id）| 中小企业投标团队简单 |
| 多租户隔离 | 不做 | 全局确认 |
| 权限码控制 | role == SUPER_ADMIN | Phase 1c 再做权限码 |

## 数据模型

### sys_department（新建）

继承 BaseModel（含 AuditMixin：id, created_at, updated_at, created_by, updated_by, is_deleted）。

| 字段 | 类型 | 说明 |
|---|---|---|
| dept_name | VARCHAR(100) NOT NULL | 部门名称 |
| dept_code | VARCHAR(50) UNIQUE NOT NULL | 部门编码，不可改 |
| parent_id | BIGINT nullable | 父部门 ID（NULL=顶级） |
| leader_id | BIGINT nullable | 部门负责人 user ID |
| sort_order | INTEGER default 0 | 排序 |
| status | TINYINT default 1 | 1=启用 0=停用 |

树形结构，parent_id=NULL 表示顶级部门。

### sys_user（修改）

新增两个字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| dept_id | BIGINT nullable | 所属部门 ID |
| position | VARCHAR(50) nullable | 岗位 |

## API 接口

路由前缀：`/api/v1/system`

### 部门 API（5 个）

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/departments/tree` | 部门树形结构 | 登录 |
| POST | `/departments` | 创建部门 | SUPER_ADMIN |
| GET | `/departments/{id}` | 部门详情 | 登录 |
| PUT | `/departments/{id}` | 更新部门（不可改 code） | SUPER_ADMIN |
| DELETE | `/departments/{id}` | 删除部门 | SUPER_ADMIN |

### 用户 API（5 个）

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/users` | 用户分页列表（支持 dept_id/keyword/status 筛选）| 登录 |
| POST | `/users` | 创建用户 | SUPER_ADMIN |
| PUT | `/users/{id}` | 更新用户 | SUPER_ADMIN |
| DELETE | `/users/{id}` | 删除用户（逻辑删除）| SUPER_ADMIN |
| PUT | `/users/{id}/reset-password` | 重置密码为默认值 | SUPER_ADMIN |

### 部门树查询方式

一次查全部 is_deleted=0 的部门，ORDER BY sort_order ASC, id ASC，在内存中用 _build_tree() 构建树。O(n) 复杂度。

### 删除保护

- 删除部门：有子部门 → 拒绝；有用户 → 拒绝
- 更新部门：不允许 parent_id == 自身 id
- 删除用户：逻辑删除

### 用户查询参数

| 参数 | 类型 | 说明 |
|---|---|---|
| page | int | 页码 |
| page_size | int | 每页条数 |
| dept_id | int? | 按部门筛选 |
| keyword | str? | 姓名/手机号模糊搜索 |
| status | int? | 状态筛选 |

## 前端

### 路由

| 路由 | 页面 |
|---|---|
| `/system/department` | 组织架构管理 |
| `/system/user` | 用户管理 |

### 侧边栏菜单

```
仪表盘
系统管理
  ├── 组织架构
  ├── 用户管理
  └── 数据字典
```

### 组织架构页（/system/department）

左右分栏：
- 左侧 300px：Ant Design Tree 组件，defaultExpandAll，点击节点选中
- 右侧：
  - 未选中：Empty 占位
  - 选中：部门详情（Descriptions）+ 操作按钮（编辑/删除/新增子部门）
- 新增/编辑弹窗：部门名称*、部门编码*（编辑时 disabled）、上级部门（TreeSelect，可为空=顶级）、排序号、状态

### 用户管理页（/system/user）

左右分栏：
- 左侧 240px：部门树（Tree），点击筛选右侧用户
- 右侧：
  - 搜索栏：关键词、状态下拉
  - 用户表格：用户名、姓名、手机、部门、岗位、角色、状态、操作
  - 新增/编辑弹窗：用户名*（编辑时 disabled）、密码*（仅新增）、姓名*、手机、邮箱、部门（TreeSelect）、岗位、角色（Select）、状态
  - 重置密码按钮

### 前端类型新增

```typescript
interface Department {
  id: number;
  dept_name: string;
  dept_code: string;
  parent_id?: number;
  leader_id?: number;
  sort_order: number;
  status: number;
  children?: Department[];
}

interface SystemUser {
  id: number;
  username: string;
  real_name: string;
  phone?: string;
  email?: string;
  avatar?: string;
  dept_id?: number;
  dept_name?: string;
  position?: string;
  role: string;
  status: number;
  last_login_at?: string;
  created_at?: string;
}
```

## 初始化数据

后端启动时：
1. 创建默认部门"总经办"（dept_code=ROOT，parent_id=NULL）
2. 将 admin 用户的 dept_id 设为该部门 ID

## 验收标准

1. 后端 10 个 API 全部可用
2. 启动后自动创建默认部门，admin 分配到该部门
3. 部门树页面正常渲染，支持增删改
4. 用户管理页面正常渲染，支持按部门筛选
5. 创建用户可选择部门
6. 删除有子部门/用户的部门被拒绝
7. 重置密码功能正常
8. TypeScript 编译无错误
9. Vite 构建成功
