# 招投标管理平台 - 项目规范

## 项目概述

面向中小企业的招投标全流程管理平台，覆盖"招标信息采集 → 投标决策 → 标书编制 → 开标跟踪 → 复盘沉淀"全链路。核心差异化：**招投标过程管理 + AI标书编制**一体化，区别于市面上纯AI标书生成工具。

- **目标客户**：有投标需求的中小企业（印刷厂、IT公司、广告公司、工程公司等）
- **核心价值**：帮企业多中标、少废标、省人力
- **行业定位**：行业无关，通用型

## 功能模块

| 模块 | 路由前缀 | 说明 |
|---|---|---|
| 认证 | `/auth` | 登录、注册 |
| 仪表盘 | `/dashboard` | 经营大盘（在投项目、中标率、近期截止、待办事项） |
| 招标管理 | `/tender` | 招标信息采集、跟踪、日历视图、到期提醒 |
| 投标决策 | `/decision` | 决策评估、审批流程、风险分析 |
| 标书编制 | `/bid` | AI解析招标文件、框架生成、内容编写、协作、AI标书检测 |
| 企业资料库 | `/library` | 资质证书、业绩案例、人员证书、产品/设备库 |
| 开标跟踪 | `/opening` | 开标结果、竞标分析、复盘记录 |
| 标书知识库 | `/knowledge` | 历史标书归档、方案模板、复用检索 |
| 审批中心 | `/workflow` | 审批流程配置、我的审批、审批记录 |
| 系统管理 | `/system` | 组织架构、用户角色、数据字典、系统配置 |

## 技术栈

### 前端
- React 18 + TypeScript (strict mode)
- Vite 构建，开发端口 **5180**
- UI 组件库: Ant Design 5
- 状态管理: Zustand
- HTTP: Axios，baseURL = `/api/v1`
- 路由: React Router v6
- 样式: Ant Design 主题 Token + CSS Variables
- 图表: ECharts
- 文档预览: PDF.js（招标文件预览）

### 后端
- Python FastAPI，运行端口 **8002**
- ORM: SQLAlchemy 2.0+ (开发环境 SQLite `data/bid.db`，生产 MySQL/PostgreSQL)
- 验证: Pydantic 2.5+
- 认证: JWT (HS256)，access_token 120min，refresh_token 30天
- AI: 火山引擎豆包 doubao-seed-1.8（招标文件解析、标书内容生成、标书检测）
- 文件处理: python-docx（Word生成/导出）、PyMuPDF（PDF解析/PDF转图片嵌入Word）

### 基础设施
- Vite 代理: `/api` → `http://localhost:8002`

## 关键约定

### API 协议
- 统一响应: `{ code: 200, message: "success", data: T, timestamp: int }`
- 分页响应: `{ code: 200, data: { items: T[], total, page, page_size, total_pages } }`
- 错误响应: `{ code: <status>, message: "<error>", data: null }`
- 路由前缀: `/api/v1/{module}/...`

### 命名规范
- **后端 Schema 是唯一真相来源**，前端类型必须对齐后端 Pydantic Schema
- 前后端字段统一 **snake_case**，不做驼峰转换
- 前端类型集中定义在 `frontend/src/types/api.ts`
- 前端 API 调用必须带泛型: `apiClient.get<APIResponse<T>>(...)`

### 前端规范
- 路径别名: `@/` → `src/`
- API 层: `frontend/src/api/`，每模块一个文件
- 页面: `frontend/src/pages/{Module}/`
- 公共组件: `frontend/src/components/`
- Store: `frontend/src/stores/`

### 后端规范
- 分层: routers → services → repositories → models
- Schema: `backend/app/schemas/`
- Model: `backend/app/models/`
- Service: `backend/app/services/`
- Router: `backend/app/routers/`

### 数据库
- 开发: SQLite (`backend/data/bid.db`)
- 生产: MySQL 8.0 / PostgreSQL 15
- 测试账号: admin/admin123
- 所有表 utf8mb4，主键 `id BIGINT AUTO_INCREMENT`
- 审计字段: created_at, updated_at, created_by, updated_by, is_deleted
- 金额: DECIMAL(14,4)，单位万元

### UI 设计规范

科技青 Teal 设计系统（区别于建筑ERP的Indigo紫）：

| 用途 | 色值 |
|---|---|
| 主色 | #0d9488 (Teal) |
| 主色渐变 | linear-gradient(135deg, #0d9488, #14b8a6) |
| 页面背景 | #f1f5f9 |
| 侧边栏背景 | #042f2e |
| 主文字 | #0f172a |

---

## 研发流程

### 需求到上线全流程（集成 Superpowers Skills）

每个步骤标注了对应的 superpowers skill（通过 `Skill` 工具调用），skill 会自动引导执行规范化流程。

```
用户/PM提需求
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  1. PM 需求分析与任务拆解                              │
│  - 明确需求范围和验收标准                              │
│  - 拆解为可执行的子任务                                │
│  - 创建任务清单                                       │
│  skill: superpowers:brainstorming（探索需求和设计）    │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  2. 架构师 技术方案评审                                │
│  - 设计 Schema / API 契约 / 技术方案文档               │
│  skill: superpowers:writing-plans（写实现计划）        │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  3. PM 确认方案                                       │
│  - 审核技术方案是否满足需求                            │
│  - 确认后通知研发和测试                                │
└──────┬───────────────┬───────────────────────────────┘
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────────────────────────────┐
│ 4a. 研发执行 │ │ 4b. 测试准备（TDD）                    │
│ 前端+后端    │ │ 编写测试用例+验收标准                   │
│ 并行开发     │ │ skill: superpowers:test-driven-        │
│              │ │    development（先写测试再实现）         │
└──────┬───────┘ └────────┬────────────────────────────┘
       │                  │
       │  skill: superpowers:dispatching-parallel-agents
       │     （2+独立任务时并行派发 agent）
       │  skill: superpowers:executing-plans
       │     （按计划逐步执行+检查点）
       │                  │
       ▼                  │
┌──────────────────────────┤
│ 5. 研发完成，验证通过     │
│ skill: superpowers:       │
│    verification-before-  │
│    completion            │
│ （必须跑验证命令，        │
│   有证据才能声称完成）     │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  6. 代码审查                                          │
│  skill: superpowers:requesting-code-review             │
│  （审查代码质量、安全性、是否符合架构设计）              │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  7. 测试执行                                          │
│  - 接口测试: curl/httpx 验证响应                       │
│  - 页面实操测试: 启动项目，实际点击页面验证              │
│  - 回归测试: 确认未破坏其他功能                        │
│  - 有 bug → skill: superpowers:systematic-debugging    │
│    （系统化排查，不猜测不盲试）                         │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  8. 测试报告                                          │
│  - 输出测试报告到 docs/ 目录                           │
│  - 反馈给 PM 和用户                                   │
│  - 有 bug → 打回研发修复 → 重测                        │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  9. PM + 用户确认验收                                  │
│  - 确认功能符合需求                                    │
│  - 确认测试报告无遗留问题                              │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  10. 完成分支                                         │
│  skill: superpowers:finishing-a-development-branch     │
│  （验证测试 → 选择合并/PR/保留 → 清理）                │
│  - commit 到主分支                                    │
│  - 更新 RELEASE_NOTES.md                              │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│  11. 部署                                             │
│  - 服务器部署流程                                     │
└──────────────────────────────────────────────────────┘
```

### Superpowers Skills 速查

| Skill | 触发时机 | 核心规则 |
|---|---|---|
| `superpowers:brainstorming` | 创建功能、修改行为之前 | 先探索需求和设计，再动手 |
| `superpowers:writing-plans` | 有需求要写实现计划时 | 输出结构化计划文档，含任务分解 |
| `superpowers:executing-plans` | 有计划要执行时 | 逐步执行+检查点，遇阻停下来问 |
| `superpowers:test-driven-development` | 实现功能或修bug之前 | 先写测试用例，再写实现代码 |
| `superpowers:dispatching-parallel-agents` | 2+独立任务可并行时 | 每个agent一个独立问题域，互不干扰 |
| `superpowers:verification-before-completion` | 声称完成之前 | 必须跑验证命令，有证据才能声称通过 |
| `superpowers:requesting-code-review` | 完成实现后、测试前 | 审查代码质量和架构一致性 |
| `superpowers:systematic-debugging` | 遇到bug或测试失败时 | 系统化排查根因，不猜测不盲试 |
| `superpowers:finishing-a-development-branch` | 实现完成+测试通过后 | 验证→选择合并方式→清理 |
| `superpowers:receiving-code-review` | 收到审查反馈时 | 技术严谨验证，不盲目同意 |

### 角色协作规则

| 阶段 | 主导角色 | 配合角色 | 输出物 | Skill |
|---|---|---|---|---|
| 需求分析 | PM | 用户 | 任务清单 + 验收标准 | brainstorming |
| 技术方案 | 架构师 | PM | Schema + API 契约 + 技术方案 | writing-plans |
| 方案确认 | PM | 用户 | 确认通知 | — |
| 测试用例 | 测试 | PM | 测试用例文档 | test-driven-development |
| 研发执行 | 前端+后端 | 架构师 | 代码实现 | executing-plans, dispatching-parallel-agents |
| 研发验证 | 前端+后端 | — | 验证通过证据 | verification-before-completion |
| 代码审查 | code-reviewer | 研发 | 审查报告 | requesting-code-review |
| 测试执行 | 测试 | 研发(修bug) | 测试报告 (docs/) | systematic-debugging（修bug时） |
| 验收确认 | PM + 用户 | 测试 | 验收通过/打回 | — |
| 代码提交 | PM | — | Git commit + Release Notes | finishing-a-development-branch |

### 测试规范（重要）

**测试工程师必须进行页面实操测试**，不能仅做接口测试或代码审查。

测试分四层:
1. **接口测试** — curl/httpx 验证 API 请求响应格式和数据正确性
2. **页面实操测试（Playwright E2E）** — 用 Playwright 自动化测试，真正打开浏览器:
   - 页面是否正常渲染（不是空白/mock数据）
   - 点击是否跳转到正确页面
   - 数据是否正确展示（不是 undefined/null）
   - 交互流程是否完整可走通（登录→操作→验证）
   - 运行: `npx playwright test`
3. **回归测试** — 确认修改未破坏其他已有功能
4. **构建验证** — TypeScript 编译 + Vite 构建

历史教训（从其他项目沉淀）:
- 接口返回正常 ≠ 页面正常（数据绑定错误、字段名不一致、mock数据覆盖）
- Vite 代理端口错误 → 全部 API 失败 → 静默 fallback 到 mock → 看起来"正常"
- ORM relationship 和 Schema 字段名冲突 → 500 错误只在运行时暴露
- **任何 bug 修复完成后，必须实际验证通过才能报告完成**

---

## AgentTeam 成员

| 角色 | Agent | 职责 |
|---|---|---|
| PM | pm-agent | 需求管理、任务拆解、团队协调、部署审批、质量把关 |
| 架构师 | architect-agent | 系统架构、数据库建模、API契约、技术方案评审 |
| 前端工程师 | frontend-agent | React + TypeScript + Ant Design 页面、组件、交互、样式 |
| 后端工程师 | backend-agent | FastAPI 接口、业务逻辑、数据库、文件处理 |
| AI工程师 | ai-agent | Claude API集成、招标文件解析、标书内容生成、废标检查算法 |
| 测试工程师 | qa-agent | 接口测试 + **页面实操测试(Playwright E2E)** + 回归测试 |

---

## 启动项目

```bash
# 后端
cd backend && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002

# 前端
cd frontend && npm run dev
```

## 部署

### 生产服务器

与建筑ERP、棋育平台共用同一台阿里云服务器，按路径分发：

- **IP**: 118.31.237.111
- **SSH**: `ssh root@118.31.237.111`
- **标书系统路径**: `http://118.31.237.111/bid/`
- **后端端口**: :8004（建筑ERP用:8000，棋育用:8001）
- **服务目录**: `/opt/bid-system/`
- **systemd**: `bid-system.service`

```
Nginx(:80)
  ├── /          → 建筑ERP 前端   + /api/       → :8000
  ├── /chess/    → 棋育 前端      + /chess/api/  → :8001
  └── /bid/     → 标书系统 前端   + /bid/api/    → :8004
```

## 项目进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 0 | 项目初始化、脚手架搭建 | ✅ 已完成 |
| Phase 1 | 基础模块（认证+权限+组织架构+审批引擎+数据字典） | ✅ 已完成 |
| Phase 2 | 招标管理 + 投标决策 + 开标跟踪 | ✅ 已完成 |
| Phase 3 | 企业资料库（资质/业绩/人员/产品） | ✅ 已完成 |
| Phase 4 | 标书编制工作台（AI解析+框架生成+内容编写+标书检测） | ✅ 已完成 |
| Phase 5 | 标书知识库 + 投标复盘 + 数据看板 | 🔧 知识库已完成，复盘/看板待做 |
| Phase 6 | 部署上线 | ✅ 已上线（118.31.237.111/bid/） |

### 近期更新记录（2026-04-15 ~ 2026-04-25）

#### 标书框架优化
- 标准框架从 15 个章节扩充到 **25 个章节**（针对政采印刷行业）
- 新增防废标章节：法定代表人身份证明书、中小企业声明函、财务状况证明、信用记录查询截图
- 新增技术加分章节：印刷工艺及色彩管理方案、项目实施进度计划、保密措施、绿色印刷及环保措施、安全生产方案、技术偏离表
- 模板匹配算法优化：从 OR 任一关键词改为按命中数排序
- 日期替换改为仅替换签章处日期，不覆盖模板中的固定日期

#### 企业信息配置化
- `config.py` 新增企业信息字段（公司名称/地址/电话/法人/信用代码/银行等）
- 模板填充自动替换 `{公司名称}` `{法定代表人}` 等占位符
- 知识库模板全部清洗（去旧项目信息、去硬编码序号、用占位符替代）

#### 资料库填充功能
- 新增「填充资料库」按钮，一键将企业资料库数据填充到 LIBRARY 类型章节
- 附件引用标记 `[附件:path:name]`，前端渲染为可点击链接，导出 Word 时 PDF 转图片嵌入

#### Word 导出美化
- 封面：项目名称 + "响应文件"大字 + 供应商信息 + 日期
- 目录：带中文序号的表格式目录
- 正文：章节标题带中文序号（一、二、三...），黑体三号加粗
- 正文字体：仿宋_GB2312 四号，1.5倍行距，首行缩进
- Markdown 解析：`##` 标题、`**加粗**`、列表、表格自动转 Word 格式
- 附件嵌入：PDF 每页转 150DPI 图片嵌入文档，图片直接嵌入
- 页码：底部居中，每章自动分页

#### 文档预览功能
- 新增「文档预览」按钮，右侧 Drawer 展示全部章节内容
- 空章节显示提示（AI生成/手动填写/资料库导入）
- 点击章节标题跳转到编辑

#### AI 标书检测（A 版）
- 替换旧的「废标检查」为「标书检测」
- 双层检测架构：规则预检（即时，不调 AI）+ AI 逐类检测（5 轮独立调用）
- 规则预检：空章节、字数不足、签章缺失、附件缺失
- AI 检测 5 个类别：资格条件、评分覆盖、技术响应、商务风险、格式合规
- 检测结果持久化（bid_check_report 表），支持历史报告查看
- SSE 流式推送检测进度，前端实时显示
- 分类 Tab 展示报告（全部/规则预检/资格条件/评分覆盖/技术响应/商务风险/格式合规）
- 设计文档：`docs/superpowers/specs/2026-04-16-bid-detection-design.md`

#### 部署
- 已部署到阿里云服务器 118.31.237.111，端口 8004
- Nginx 配置：`/bid/` 前端静态 + `/bid/api/` 反代到 :8004
- systemd 服务：`bid-system.service`
- 前端 `base` 路径适配（vite.config.ts + api.ts + request.ts）

#### AI 模型
- 从 doubao-seed-1.6 升级到 **doubao-seed-1.8**
- 效果提升：专业度更高，更贴合政采实操，语言更自然
- 成本：约 ¥1/份标书（含解析+生成+检测），月产30份约 ¥30

#### 招标文件章节模板抽取（2026-04-25）
- 改造「一键填入招标信息」按钮：解析招标文件时**一次性**把每章对应的模板原文（响应函格式、报价表样式、承诺函格式等）一并抽出，直接填入 `section.content`，不再只生成空章节
- 设计演进：
  - 初版方案：第一次解析只拿章节名 + 用户点「一键填入」时第二次 AI 调用抽取模板 → 复杂、慢、贵
  - **最终方案**：合并为单次 AI 调用，模板抽取直接写入 parse_result，框架生成只读缓存零 AI 调用
- 后端：`tender_ai_parser.parse()` 的 prompt 中 `chapters` 字段输出 `[{title, section_type, template, matched}]`，max_tokens 提至 16384；`bid_framework_service.generate_from_tender()` 直接读 parse_result.chapters，兼容旧版字符串数组
- 章节合并规则：解析章节 + 必备 fallback（中小企业声明函/无重大违法记录声明函/法定代表人身份证明书/授权委托书）+ 末尾「补充信息」LIBRARY 章节
- 前端：`TenderDocParser` 简化进度面板（生成瞬时完成无需阶段提示）+ `Workbench` 中「一键生成框架（标准模板）」按钮在已解析项目中隐藏
- 升级时机：旧的招标文件解析结果只有章节名没有模板，需重新上传招标文件即可拿到带模板的解析结果
- 设计文档：`docs/superpowers/specs/2026-04-25-tender-template-extract-design.md`
- 实施计划：`docs/superpowers/plans/2026-04-25-tender-template-extract.md`
- 测试报告：`docs/test-reports/2026-04-25-tender-template-extract-test-report.md`
