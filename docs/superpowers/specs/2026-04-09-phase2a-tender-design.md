# Phase 2a 设计：招标管理

> 日期：2026-04-09
> 状态：已确认

## 数据模型

### tender（招标信息表）

继承 BaseModel（含 AuditMixin）。

| 字段 | 类型 | 说明 |
|---|---|---|
| title | VARCHAR(200) NOT NULL | 项目名称 |
| tender_no | VARCHAR(100) | 招标编号 |
| tender_unit | VARCHAR(200) | 招标单位 |
| tender_method | VARCHAR(50) | 招标方式（字典 tender_method） |
| info_source | VARCHAR(50) | 信息来源（字典 tender_source） |
| province | VARCHAR(50) | 省份 |
| city | VARCHAR(50) | 城市 |
| budget_amount | DECIMAL(14,4) | 预算金额（万元） |
| deposit_amount | DECIMAL(14,4) | 保证金金额（万元） |
| deposit_deadline | DATETIME | 保证金截止时间 |
| reg_deadline | DATETIME | 报名截止时间 |
| open_bid_time | DATETIME | 开标时间 |
| status | VARCHAR(20) DEFAULT 'PENDING' | 跟进状态（字典 bid_status） |
| follower_id | BIGINT | 跟进人 user ID |
| remark | TEXT | 备注 |

## API 接口

路由前缀：`/api/v1/tender`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/list` | 招标列表（分页+筛选） | 登录 |
| POST | `/` | 创建招标信息 | 登录 |
| GET | `/{id}` | 招标详情 | 登录 |
| PUT | `/{id}` | 更新招标信息 | 登录 |
| DELETE | `/{id}` | 删除招标信息 | SUPER_ADMIN |
| PUT | `/{id}/status` | 更新跟进状态 | 登录 |
| PUT | `/{id}/follower` | 分配跟进人 | 登录 |
| GET | `/calendar` | 日历数据（按月查询） | 登录 |
| GET | `/stats` | 统计概览（各状态数量） | 登录 |
| GET | `/expiring` | 近期到期提醒（7天内） | 登录 |

### 筛选参数（GET /list）

| 参数 | 类型 | 说明 |
|---|---|---|
| page / page_size | int | 分页 |
| keyword | str? | 项目名称/招标编号模糊搜索 |
| tender_method | str? | 招标方式 |
| info_source | str? | 信息来源 |
| status | str? | 跟进状态 |
| follower_id | int? | 跟进人 |
| start_date / end_date | str? | 开标时间范围 |

### 日历数据（GET /calendar）

参数：year, month
返回：该月内所有招标信息的关键日期列表
```json
[
  { "id": 1, "title": "XX项目", "date": "2026-04-15", "type": "reg_deadline", "label": "报名截止" },
  { "id": 1, "title": "XX项目", "date": "2026-04-20", "type": "open_bid", "label": "开标" }
]
```

### 统计概览（GET /stats）

```json
{
  "total": 25,
  "pending": 8,
  "decided_bid": 10,
  "decided_give_up": 3,
  "composing": 2,
  "submitted": 1,
  "opened": 1
}
```

### 到期提醒（GET /expiring）

返回 7 天内有截止日期（报名截止/保证金截止/开标时间）的招标信息列表。

## 前端

### 路由

| 路由 | 页面 |
|---|---|
| `/tender/list` | 招标列表 |
| `/tender/create` | 新增招标 |
| `/tender/:id` | 招标详情/编辑 |
| `/tender/calendar` | 日历视图 |

### 侧边栏菜单

```
仪表盘
招标管理
  ├── 招标列表
  └── 日历视图
审批中心
系统管理
  ├── ...
```

### 招标列表页（/tender/list）

- 顶部：筛选栏（关键词、招标方式、信息来源、状态、跟进人、时间范围）
- 表格列：项目名称、招标编号、招标单位、招标方式、预算金额、开标时间、状态、跟进人、操作
- 状态用彩色 Tag：待评估(蓝)、已决策-投标(绿)、已决策-放弃(灰)、编制中(橙)、已提交(紫)、已开标(默认)
- 操作：查看、编辑、删除

### 招标表单页（/tender/create 和 /tender/:id）

分区表单：
- 基本信息：项目名称*、招标编号、招标单位、招标方式（Select 字典）、信息来源（Select 字典）
- 地区信息：省份、城市
- 财务信息：预算金额、保证金金额、保证金截止时间
- 时间信息：报名截止时间、开标时间
- 其他：跟进状态（Select 字典）、跟进人（Select 用户）、备注

### 日历视图页（/tender/calendar）

- Ant Design Calendar 组件
- 每个日期格子内显示当天的事件（报名截止/保证金截止/开标）
- 事件用不同颜色 Tag 区分
- 点击事件跳转到招标详情

### 前端类型

```typescript
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

interface TenderCalendarItem {
  id: number;
  title: string;
  date: string;
  type: 'reg_deadline' | 'deposit_deadline' | 'open_bid';
  label: string;
}

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

## 验收标准

1. 10 个 API 全部可用
2. 招标列表页筛选、分页正常
3. 新增/编辑招标信息正常
4. 状态更新正常
5. 日历视图展示关键日期
6. 统计概览数据正确
7. 到期提醒返回 7 天内截止项
8. TypeScript 编译 + Vite 构建通过
