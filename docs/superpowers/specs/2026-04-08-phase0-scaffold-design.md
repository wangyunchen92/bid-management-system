# Phase 0 设计：项目脚手架搭建

> 日期：2026-04-08
> 状态：待审核
> 方案：从现有建筑 ERP 复制精简（方案 A）

## 背景

招投标管理平台是独立于建筑 ERP 的新产品，面向所有有投标需求的中小企业。技术栈与 ERP 完全一致（FastAPI + React + Ant Design + Vite），约 70% 基础设施代码可从 ERP 复用。

Phase 0 目标：搭建前后端项目骨架，跑通登录流程，为后续 Phase 1（基础模块）提供可运行的代码基座。

## 技术决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 搭建方式 | 从 ERP 复制精简 | ERP 经过 286 API + 90 页面验证，架构成熟 |
| 前端端口 | 5180 | 避免与其他项目冲突 |
| 后端端口 | 8002 | 与 ERP(:8000)、棋育(:8001) 共存 |
| 数据库 | SQLite（开发）| 零配置，快速启动 |
| 多租户 | 暂不引入 | Phase 0 不需要，后续按需加回 |
| Celery/Redis/MinIO | 暂不引入 | 初期无异步任务和文件存储需求 |

## 项目结构

```
标书系统/
├── CLAUDE.md
├── agents/
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts              # 端口 5180，代理 /api → localhost:8002
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── app.tsx                  # Ant Design 主题（Teal #0d9488）
│       ├── routes.tsx               # /login + /dashboard 占位
│       ├── access.ts                # 权限框架（清空业务权限码）
│       ├── layouts/
│       │   ├── BasicLayout.tsx      # 侧边栏布局，Logo"招投标管理平台"
│       │   └── BlankLayout.tsx      # 登录页空白布局
│       ├── pages/
│       │   ├── Login/
│       │   └── Dashboard/           # 占位页
│       ├── components/
│       ├── services/
│       │   └── auth.ts
│       ├── stores/
│       │   └── useAuthStore.ts
│       ├── hooks/
│       ├── utils/
│       │   └── auth.ts              # Token 存取
│       ├── types/
│       │   └── api.ts               # 通用响应类型
│       ├── constants/
│       └── styles/
│           └── global.css           # Teal 设计系统 CSS 变量
│
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py                  # FastAPI 入口
│       ├── config.py                # APP_NAME=bid-system, DB=data/bid.db
│       ├── database.py              # SQLAlchemy async + SQLite
│       ├── common/
│       │   ├── security.py          # JWT（无 tenant_id）
│       │   ├── deps.py              # get_current_user（无多租户）
│       │   ├── response.py          # 统一响应格式
│       │   ├── exceptions.py        # 业务异常类
│       │   └── pagination.py        # 分页工具
│       ├── models/
│       │   └── system.py            # SysUser 单表
│       ├── schemas/
│       │   └── auth.py
│       ├── services/
│       │   └── auth.py
│       ├── routers/
│       │   └── auth.py
│       ├── repositories/
│       └── data/
│           └── .gitkeep
│
└── deploy/
    ├── deploy.sh
    ├── upload.sh
    └── README.md
```

## 数据模型

### sys_user

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 自增主键 |
| username | VARCHAR(50) | 登录名，唯一 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| real_name | VARCHAR(50) | 真实姓名 |
| phone | VARCHAR(20) | 手机号 |
| email | VARCHAR(100) | 邮箱 |
| role | VARCHAR(20) | 角色（SUPER_ADMIN / ADMIN / USER） |
| status | TINYINT | 1=启用 0=禁用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| is_deleted | TINYINT | 软删除标记 |

无多租户字段。后续需要时加 `tenant_id` 列。

## API 接口

| 方法 | 路径 | 说明 | 认证 |
|---|---|---|---|
| POST | `/api/v1/auth/login` | 登录 | 否 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | 否（Bearer refresh_token） |
| GET | `/api/v1/auth/me` | 获取当前用户 | 是 |
| PUT | `/api/v1/auth/password` | 修改密码 | 是 |
| GET | `/api/health` | 健康检查 | 否 |

### 响应格式

```json
// 成功
{ "code": 200, "message": "success", "data": { ... }, "timestamp": 1712534400 }

// 失败
{ "code": 401, "message": "用户名或密码错误", "data": null, "timestamp": 1712534400 }

// 登录成功 data
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer" }
```

## 从 ERP 复制时的改动清单

### 前端

| 文件 | 改动 |
|---|---|
| `package.json` | name→`bid-system-frontend`，去掉 pro-components/pro-layout/echarts |
| `vite.config.ts` | 端口→5180，代理→localhost:8002 |
| `app.tsx` | 删除通知轮询 |
| `routes.tsx` | 删除业务路由，只留 /login + /dashboard |
| `BasicLayout.tsx` | Logo→"招投标管理平台"，清空菜单，删除通知 Popover |
| `useAuthStore.ts` | 删除 register、tenantName |
| `global.css` | 改注释，CSS 变量保留 |

### 后端

| 文件 | 改动 |
|---|---|
| `main.py` | 标题→"招投标管理平台"，只注册 auth 路由，清空字典初始化，去掉租户中间件 |
| `config.py` | APP_NAME→bid-system，DB→data/bid.db，端口→8002 |
| `requirements.txt` | 去掉 celery/redis/minio/aiomysql，加 aiosqlite |
| `security.py` | token payload 去掉 tenant_id |
| `deps.py` | 去掉 tenant_id 相关函数和调用 |
| `models/system.py` | 只保留 SysUser（无 tenant_id） |
| `exceptions.py` | 去掉 ApprovalException |

### 初始化数据

启动时自动创建：
- 默认管理员：`admin / admin123`，角色 `SUPER_ADMIN`

## 验收标准

1. `cd backend && python3 -m uvicorn app.main:app --reload --port 8002` — 启动成功
2. `cd frontend && npm install && npm run dev` — 启动成功，端口 5180
3. 浏览器 `localhost:5180` → 自动跳转登录页
4. `admin / admin123` 登录 → 进入仪表盘占位页
5. `npx tsc --noEmit` — TypeScript 编译无错误
6. `npm run build` — Vite 构建成功
7. `curl localhost:8002/api/health` — 返回 200
