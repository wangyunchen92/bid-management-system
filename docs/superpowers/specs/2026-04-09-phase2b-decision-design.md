# Phase 2b 设计：投标决策

> 日期：2026-04-09
> 状态：已确认

## 业务流程

```
招标信息(PENDING) → 创建投标决策 → 发起审批 → 通过: tender→DECIDED_BID, decision→PASS
                                              → 驳回: tender→DECIDED_GIVE_UP, decision→REJECT
```

## 数据模型

### bid_decision（投标决策表）

继承 BaseModel（含 AuditMixin）。

| 字段 | 类型 | 说明 |
|---|---|---|
| tender_id | BIGINT NOT NULL | 关联招标信息 ID |
| decision_reason | TEXT | 投标理由/分析 |
| risk_analysis | TEXT | 风险分析 |
| estimated_amount | DECIMAL(14,4) | 预估报价（万元） |
| win_probability | INTEGER | 预估中标概率（0-100%） |
| competitors | TEXT | 已知竞争对手 |
| decision_result | VARCHAR(20) DEFAULT 'PENDING' | 决策结果 PENDING/PASS/REJECT |
| approval_id | BIGINT | 关联审批实例 ID |
| initiator_id | BIGINT NOT NULL | 发起人 user ID |
| remark | TEXT | 备注 |

## API 接口

路由前缀：`/api/v1/decision`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/list` | 决策列表（分页+筛选） | 登录 |
| POST | `/` | 创建决策（同时发起审批） | 登录 |
| GET | `/{id}` | 决策详情（含审批信息） | 登录 |
| PUT | `/{id}` | 更新决策 | 登录 |
| DELETE | `/{id}` | 删除决策 | SUPER_ADMIN |
| GET | `/by-tender/{tender_id}` | 按招标查决策 | 登录 |

### 创建决策请求

```json
{
  "tender_id": 1,
  "decision_reason": "预算充足，技术匹配",
  "risk_analysis": "竞争对手较多",
  "estimated_amount": 85.5,
  "win_probability": 60,
  "competitors": "A公司、B公司",
  "approver_id": 1,
  "remark": ""
}
```

创建时自动：
1. 创建 bid_decision 记录
2. 调用 approval_service.submit 发起审批（biz_type=BID_DECISION, biz_id=decision.id）
3. 将 approval_id 写回 decision

### 审批联动

审批引擎的 approve/reject 操作后，需要同步更新决策和招标状态。
实现方式：在 approval_service 的 approve/reject 方法中添加回调逻辑：
- approve 且 biz_type==BID_DECISION → decision.decision_result=PASS, tender.status=DECIDED_BID
- reject 且 biz_type==BID_DECISION → decision.decision_result=REJECT, tender.status=DECIDED_GIVE_UP

### 筛选参数（GET /list）

| 参数 | 说明 |
|---|---|
| keyword | 招标项目名称模糊搜索 |
| decision_result | PENDING/PASS/REJECT |
| initiator_id | 发起人 |

### 决策详情响应

包含关联的招标信息摘要（title, tender_no, tender_unit）和审批状态。

## 前端

### 路由

| 路由 | 页面 |
|---|---|
| `/decision/list` | 投标决策列表 |

### 侧边栏

```
招标管理
投标决策
审批中心
系统管理
```

### 投标决策列表页（/decision/list）

- 表格列：招标项目、预估报价、中标概率、决策结果(Tag)、发起人、审批状态、创建时间、操作
- 决策结果 Tag：PENDING=blue, PASS=green, REJECT=red
- 操作：查看详情、编辑（仅 PENDING）、删除
- 新增按钮 → 弹窗表单

### 新增/编辑弹窗

- 选择招标项目（Select，从招标列表获取 PENDING 状态的）
- 投标理由（TextArea）
- 风险分析（TextArea）
- 预估报价（InputNumber 万元）
- 中标概率（Slider 0-100%）
- 竞争对手（TextArea）
- 审批人（Select 用户列表）— 仅新增时
- 备注

### 决策详情弹窗

显示决策完整信息 + 关联审批记录（Timeline）

## 验收标准

1. 6 个 API 全部可用
2. 创建决策时自动发起审批
3. 审批通过 → 决策 PASS + 招标 DECIDED_BID
4. 审批驳回 → 决策 REJECT + 招标 DECIDED_GIVE_UP
5. 审批中心能看到投标决策的审批待办
6. 前端决策列表页正常
7. TS 编译 + Vite 构建通过
8. **页面实操测试**：启动前后端，在浏览器中走通完整流程
