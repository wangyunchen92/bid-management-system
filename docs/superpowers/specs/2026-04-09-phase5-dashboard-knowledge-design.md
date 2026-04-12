# Phase 5 设计：仪表盘 + 标书知识库

> 日期：2026-04-09
> 状态：已确认

## 5a. 仪表盘（数据看板）

### 后端接口

`GET /api/v1/dashboard/stats` — 仪表盘统计数据，一个接口返回全部：

```json
{
  "cards": {
    "active_tenders": 12,
    "win_count_year": 5,
    "win_rate": 62.5,
    "expiring_7days": 3
  },
  "status_distribution": [
    { "status": "PENDING", "label": "待评估", "count": 5 },
    { "status": "DECIDED_BID", "label": "已决策-投标", "count": 3 },
    ...
  ],
  "monthly_trend": [
    { "month": "2026-01", "bid_count": 8, "win_count": 3 },
    { "month": "2026-02", "bid_count": 10, "win_count": 5 },
    ...
  ],
  "expiring_list": [
    { "id": 1, "title": "XX项目", "deadline_type": "reg_deadline", "deadline": "2026-04-15", "days_left": 3 }
  ],
  "pending_approvals": [
    { "id": 1, "title": "投标决策：XX项目", "initiator_name": "张三", "created_at": "..." }
  ]
}
```

### 前端页面

替换现有空仪表盘页面：
- 顶部 4 个 Statistic Card（在投项目/本年中标/中标率/即将截止）
- 中间两列图表：左=状态分布饼图、右=月度趋势折线图
- 底部两列列表：左=截止提醒、右=待办审批

图表使用 ECharts（需安装 echarts + echarts-for-react）。

## 5b. 标书知识库

### 数据模型

**knowledge_template（知识库模板表）**

继承 BaseModel（含 AuditMixin）。

| 字段 | 类型 | 说明 |
|---|---|---|
| title | VARCHAR(200) NOT NULL | 模板标题 |
| category | VARCHAR(50) | 分类（字典 doc_type） |
| content | TEXT | 模板内容 |
| source_project_id | BIGINT | 来源标书项目 ID |
| tags | VARCHAR(500) | 标签（逗号分隔） |
| usage_count | INTEGER DEFAULT 0 | 使用次数 |
| remark | TEXT | 备注 |

### API 接口（6 个）

路由前缀：`/api/v1/knowledge`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/list` | 列表（分页+keyword+category 筛选） |
| POST | `/` | 创建模板 |
| GET | `/{id}` | 模板详情 |
| PUT | `/{id}` | 更新模板 |
| DELETE | `/{id}` | 删除模板 |
| GET | `/search` | 搜索（按关键词+分类，返回匹配的模板列表） |

### 前端页面

路由：`/knowledge/list`

卡片列表（Card 网格，类似标书列表）：
- 每个模板一张 Card：标题、分类(Tag)、标签(Tags)、使用次数、摘要（content 前 100 字）
- 点击卡片查看详情（Modal 展示完整内容）
- 筛选：keyword 搜索 + category Select
- 新增/编辑弹窗：标题*、分类(Select)、标签(Input)、内容(TextArea)、备注

### 侧边栏

```
仪表盘          ← 改造
招标管理
投标决策
开标跟踪
企业资料库
标书编制
知识库           ← 新增
审批中心
系统管理
```

## 验收标准

1. 仪表盘接口返回完整统计数据
2. 仪表盘页面 4 个统计卡片正确显示
3. 仪表盘饼图和折线图正常渲染
4. 仪表盘截止提醒和待办列表正常
5. 知识库 6 个 API 全部可用
6. 知识库页面正常渲染，支持搜索和分类筛选
7. TypeScript 编译 + Vite 构建通过
8. **Playwright E2E 测试**：仪表盘+知识库页面
9. **回归测试**：跑 e2e-deep-test.mjs 确认未破坏已有功能
10. **测试报告输出到 docs/**
