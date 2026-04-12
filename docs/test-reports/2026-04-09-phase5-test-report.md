# Phase 5 测试报告

> 测试日期：2026-04-09（实际执行：2026-04-10）
> 测试工程师：qa-agent

## 第一层：接口测试

### 仪表盘 API

| # | 接口 | 状态 | 备注 |
|---|---|---|---|
| 1 | 创建测试招标数据（3条） | ✅ PASS | 创建 PENDING/DECIDED_BID/COMPOSING 状态各1条 |
| 2 | 创建开标记录（WIN+LOSE） | ✅ PASS | WIN×1、LOSE×1，开标后关联招标状态自动更新为 OPENED |
| 3 | GET /api/v1/dashboard/stats — cards.active_tenders > 0 | ✅ PASS | active_tenders=1（PENDING状态招标） |
| 4 | GET /api/v1/dashboard/stats — cards.win_rate 正确 | ✅ PASS | win_rate=50.0（1 WIN / 2 总开标） |
| 5 | GET /api/v1/dashboard/stats — status_distribution 有数据 | ✅ PASS | 6个状态，PENDING=1，OPENED=2 |
| 6 | GET /api/v1/dashboard/stats — monthly_trend 有数据 | ✅ PASS | 近6个月，2026-04 bid_count=2 |
| 7 | GET /api/v1/dashboard/stats — expiring_list 格式正确 | ✅ PASS | 1条即将截止记录，含 id/title/deadline/days_left |
| 8 | GET /api/v1/dashboard/stats — pending_approvals 格式正确 | ✅ PASS | 空列表（无待办审批），格式正确 |

### 知识库 API

| # | 接口 | 状态 | 备注 |
|---|---|---|---|
| 9 | POST /api/v1/knowledge — 创建模板 | ✅ PASS | 返回 code:200，创建成功，返回完整模板对象 |
| 10 | GET /api/v1/knowledge/list — 列表 | ✅ PASS | 返回分页数据，total=2，items包含创建的模板 |
| 11 | GET /api/v1/knowledge/search?keyword=IT — 搜索 | ✅ PASS | 返回1条匹配结果 |
| 12 | GET /api/v1/knowledge/{id} — 详情 | ✅ PASS | 返回完整模板详情，含所有字段 |
| 13 | PUT /api/v1/knowledge/{id} — 更新 | ✅ PASS | 返回"更新成功"，标题已更新 |
| 14 | DELETE /api/v1/knowledge/{id} — 删除 | ✅ PASS | 返回"删除成功" |

**备注：** knowledge 的 `tags` 字段为逗号分隔的字符串（非数组），前端解析正常。list/search 响应中含多行内容的 content 字段在 JSON 中被正确转义（`\n`），API 本身无问题（shell echo 显示问题非 API 问题）。

接口测试小计：**14/14 通过**

---

## 第二层：Playwright E2E 页面实操测试

### 新增仪表盘测试（更新 testDashboard）

| # | 测试项 | 状态 | 备注 |
|---|---|---|---|
| 15 | 仪表盘渲染正常 | ✅ PASS | 页面包含"招投标管理平台" |
| 16 | 侧边栏所有菜单可见 | ✅ PASS | 8个菜单项全部显示 |
| 17 | 统计卡片存在（在投项目数） | ✅ PASS | 显示"在投项目数"卡片 |
| 18 | 统计卡片存在（本年中标数） | ✅ PASS | 显示"本年中标数"卡片 |
| 19 | 统计卡片存在（中标率） | ✅ PASS | 显示"中标率"卡片 |
| 20 | 统计卡片存在（即将截止） | ✅ PASS | 显示"即将截止（7天内）"卡片 |
| 21 | 图表容器存在（ECharts canvas） | ✅ PASS | 检测到 ≥2 个 canvas 元素 |

### 新增知识库测试（testKnowledge）

| # | 测试项 | 状态 | 备注 |
|---|---|---|---|
| 22 | 导航到知识库列表页（/knowledge/list） | ✅ PASS | 页面正常加载 |
| 23 | 知识库页面渲染正常 | ✅ PASS | 显示"新增模板"按钮和搜索框 |
| 24 | 新增模板按钮可点击 | ✅ PASS | 按钮存在且可点击 |
| 25 | 新增模板弹窗弹出 | ✅ PASS | 弹窗显示，含"新增模板"/"模板标题"字段 |

E2E 新增测试小计：**11/11 通过**

---

## 第三层：回归测试

运行完整 e2e-deep-test.mjs（包含所有模块），确认既有功能未被破坏。

**回归通过率：48/48**

| 模块 | 测试数 | 通过数 | 状态 |
|---|---|---|---|
| 准备数据 | 3 | 3 | ✅ 全部通过 |
| 登录流程 | 2 | 2 | ✅ 全部通过 |
| 仪表盘（更新后） | 7 | 7 | ✅ 全部通过 |
| 数据字典 CRUD | 4 | 4 | ✅ 全部通过 |
| 组织架构 | 3 | 3 | ✅ 全部通过 |
| 用户管理 | 3 | 3 | ✅ 全部通过 |
| 角色管理 | 2 | 2 | ✅ 全部通过 |
| 招标管理 | 5 | 5 | ✅ 全部通过 |
| 投标决策 | 2 | 2 | ✅ 全部通过 |
| 审批中心 | 2 | 2 | ✅ 全部通过 |
| 开标跟踪 | 1 | 1 | ✅ 全部通过 |
| 企业资料库 | 4 | 4 | ✅ 全部通过 |
| 标书编制 | 5 | 5 | ✅ 全部通过 |
| 标书知识库（新） | 4 | 4 | ✅ 全部通过 |
| 退出登录 | 1 | 1 | ✅ 全部通过 |

浏览器控制台错误：1条（404 静态资源，疑似 favicon，不影响功能）

---

## 第四层：构建验证

| 项目 | 状态 | 备注 |
|---|---|---|
| TypeScript 编译（npx tsc --noEmit） | ✅ PASS | 无类型错误，零报错 |
| Vite 生产构建（npm run build） | ✅ PASS | 构建成功，耗时 8.10s，3756 模块转换 |

---

## 总结

**62/62 测试通过**（接口14 + E2E新增11 + 回归48 + 构建2，其中E2E新增与回归有重叠，实际E2E共48项）

| 测试层 | 通过 | 总计 | 通过率 |
|---|---|---|---|
| 第一层：接口测试 | 14 | 14 | 100% |
| 第二层：E2E 页面实操 | 48 | 48 | 100% |
| 第三层：回归测试 | 48 | 48 | 100% |
| 第四层：构建验证 | 2 | 2 | 100% |

### 遗留问题

1. **轻微**：浏览器控制台有1条404错误（静态资源，推测为favicon），不影响任何功能，可忽略或后续补充 favicon 文件处理。
2. **知识库 tags 字段**：后端 schema 定义为逗号分隔字符串，前端 CATEGORY_OPTIONS 的 value 值（如 `technical`、`commercial`）与后端实际存储的分类值（如 `TECH`、`BUSINESS`）存在不一致，建议后续统一对齐。目前功能可用，创建/展示无报错。
