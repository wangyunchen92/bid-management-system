# Phase 1d 设计：简易审批引擎

> 日期：2026-04-08
> 状态：已确认
> 升级计划：Phase 4 完成后评估是否升级为可配置审批引擎

## 设计选择

A 方案（简易审批）：固定两级审批，顺序审批，不做流程模板配置。
后续如需条件分支/会签/或签，升级为 B 方案（可配置引擎）。

## 数据模型

### approval_instance（审批实例）

继承 BaseModel（含 AuditMixin）。

| 字段 | 类型 | 说明 |
|---|---|---|
| title | VARCHAR(200) NOT NULL | 审批标题 |
| biz_type | VARCHAR(50) NOT NULL | 业务类型编码（BID_DECISION / BID_REVIEW 等） |
| biz_id | BIGINT | 关联业务记录 ID |
| initiator_id | BIGINT NOT NULL | 发起人 user ID |
| approver_id | BIGINT NOT NULL | 当前审批人 user ID |
| status | VARCHAR(20) NOT NULL DEFAULT 'PENDING' | PENDING / APPROVED / REJECTED |
| result_comment | TEXT | 审批意见 |
| approved_at | DATETIME | 审批完成时间 |

### approval_record（审批记录）

直接继承 Base，无 is_deleted。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| instance_id | BIGINT NOT NULL | 关联审批实例 ID |
| operator_id | BIGINT NOT NULL | 操作人 user ID |
| action | VARCHAR(20) NOT NULL | SUBMIT / APPROVE / REJECT / TRANSFER |
| comment | TEXT | 操作备注 |
| created_at | DATETIME | 操作时间 |

## API 接口

路由前缀：`/api/v1/approval`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/submit` | 发起审批 | 登录 |
| GET | `/my-pending` | 我的待审批列表 | 登录 |
| GET | `/my-initiated` | 我发起的审批列表 | 登录 |
| GET | `/{id}` | 审批详情（含记录） | 登录 |
| POST | `/{id}/approve` | 同意 | 登录（仅当前审批人） |
| POST | `/{id}/reject` | 驳回 | 登录（仅当前审批人） |
| POST | `/{id}/transfer` | 转审 | 登录（仅当前审批人） |

### 请求体

发起审批：
```json
{
  "title": "投标决策：XX项目招标",
  "biz_type": "BID_DECISION",
  "biz_id": 123,
  "approver_id": 1
}
```

同意/驳回：
```json
{ "comment": "同意，请尽快准备标书" }
```

转审：
```json
{ "to_user_id": 5, "comment": "请张总审批" }
```

### 审批状态机

```
SUBMIT → PENDING
  ├── APPROVE → APPROVED（终态）
  ├── REJECT → REJECTED（终态）
  └── TRANSFER → PENDING（换审批人，继续）
```

### 权限控制

- 发起审批：任何登录用户
- 审批操作（同意/驳回/转审）：仅 instance.approver_id == 当前用户
- 查看详情：发起人或审批人可查看

### 列表查询

- 我的待审批：approver_id == 当前用户 AND status == PENDING
- 我发起的：initiator_id == 当前用户，按 created_at DESC

两个列表都支持分页。返回数据中包含发起人和审批人的 real_name。

## 前端

### 路由

| 路由 | 页面 |
|---|---|
| `/workflow` | 审批中心 |

### 侧边栏菜单

```
仪表盘
审批中心
系统管理
  ├── 组织架构
  ├── 用户管理
  ├── 角色管理
  └── 数据字典
```

### 审批中心页（/workflow）

Tabs 切换：
- **我的待办**：Table 显示待审批列表，列：标题、发起人、发起时间、操作
  - 操作列：「同意」「驳回」「转审」按钮
  - 点击同意/驳回弹出 Modal 输入审批意见
  - 转审弹出 Modal 选择转审人 + 备注
- **我发起的**：Table 显示我发起的审批，列：标题、审批人、状态、发起时间
  - 状态用 Tag 展示（PENDING=蓝色、APPROVED=绿色、REJECTED=红色）
- 点击标题可查看审批详情（审批记录时间线）

### 前端类型

```typescript
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

interface ApprovalRecord {
  id: number;
  instance_id: number;
  operator_id: number;
  operator_name?: string;
  action: 'SUBMIT' | 'APPROVE' | 'REJECT' | 'TRANSFER';
  comment?: string;
  created_at?: string;
}

interface ApprovalDetail {
  instance: ApprovalInstance;
  records: ApprovalRecord[];
}
```

## 验收标准

1. 7 个 API 全部可用
2. 发起审批 → 待办列表可见
3. 同意/驳回 → 状态正确流转
4. 转审 → 换审批人，原审批人待办消失，新审批人待办出现
5. 非审批人操作被拒绝
6. 审批详情显示完整记录时间线
7. 前端审批中心页 Tab 切换正常
8. TypeScript 编译 + Vite 构建通过
