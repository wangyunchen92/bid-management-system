# Phase 1a 设计：数据字典模块

> 日期：2026-04-08
> 状态：已确认

## 背景

数据字典是其他模块的基础依赖（招标方式、投标状态、资质类型等都通过字典配置）。从 ERP 复用成熟的字典模块，去掉多租户。

## 数据模型

### sys_dict_type（字典类型）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| dict_name | VARCHAR(100) NOT NULL | 字典名称 |
| dict_code | VARCHAR(100) UNIQUE NOT NULL | 字典编码，创建后不可修改 |
| description | VARCHAR(255) | 描述 |
| status | TINYINT DEFAULT 1 | 1=启用 0=停用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| created_by | BIGINT | 创建人 |
| updated_by | BIGINT | 更新人 |
| is_deleted | TINYINT DEFAULT 0 | 逻辑删除 |

继承 BaseModel（含 AuditMixin）。

### sys_dict_item（字典项）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| dict_type_id | BIGINT NOT NULL | 关联字典类型 ID |
| item_label | VARCHAR(100) NOT NULL | 显示标签 |
| item_value | VARCHAR(100) NOT NULL | 存储值，同 dict_type_id 下唯一 |
| sort_order | INTEGER DEFAULT 0 | 排序号 |
| status | TINYINT DEFAULT 1 | 1=启用 0=停用 |
| description | VARCHAR(255) | 描述 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

不继承 BaseModel，直接继承 Base。无 is_deleted（物理删除）。无 tenant_id。

### 删除策略

- 字典类型：逻辑删除（is_deleted = 1）
- 字典项：物理删除
- 删除字典类型前检查是否有关联字典项，有则拒绝

### 唯一性约束

- dict_code 全局唯一（数据库 UNIQUE 约束 + service 层检查）
- item_value 在同一 dict_type_id 下唯一（service 层检查）

## API 接口

路由前缀：`/api/v1/system`

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/dict-types` | 字典类型分页列表 | 登录 |
| POST | `/dict-types` | 创建字典类型 | SUPER_ADMIN |
| PUT | `/dict-types/{id}` | 更新字典类型（不可改 code） | SUPER_ADMIN |
| DELETE | `/dict-types/{id}` | 删除字典类型 | SUPER_ADMIN |
| GET | `/dict-types/{id}/items` | 某字典类型的字典项列表 | 登录 |
| POST | `/dict-types/{id}/items` | 创建字典项 | SUPER_ADMIN |
| PUT | `/dict-items/{id}` | 更新字典项 | SUPER_ADMIN |
| DELETE | `/dict-items/{id}` | 删除字典项 | SUPER_ADMIN |
| GET | `/dicts/{code}` | 按编码查字典项（前端下拉用） | 登录 |

### 权限控制

Phase 0 尚无权限码系统，暂用 role 判断：
- 查询接口：登录即可（get_current_user_id）
- 增删改接口：require_super_admin 依赖（检查 user.role == "SUPER_ADMIN"）

### 响应格式

字典类型列表：分页响应 `{ items, total, page, page_size, total_pages }`
字典项列表：数组响应 `[{ id, dict_type_id, item_label, item_value, sort_order, status, description }]`
按编码查字典：同字典项列表格式，只返回 status=1 的项

## 前端

### 路由

`/system/dict` — 数据字典管理页面

### 侧边栏菜单

在 BasicLayout 的 menuItems 中新增：

```
仪表盘
系统管理
  └── 数据字典
```

### 页面布局

左右分栏：
- 左侧 280px 固定宽度：字典类型列表（Card + List 组件）
  - 顶部：标题 + 新增按钮
  - 列表项：名称、编码、状态徽标
  - 点击选中高亮（Teal 左边框 + 浅背景）
- 右侧 flex: 1：字典项表格（Card + Table 组件）
  - 未选中时显示占位提示
  - 选中后显示表格，列：显示标签、存储值（code 样式）、排序号、状态、操作
  - 表格上方：类型名称 + 新增按钮

### 弹窗

字典类型弹窗（Modal + Form）：
- 字段：类型名称*、类型编码*（编辑时 disabled）、状态开关、备注

字典项弹窗（Modal + Form）：
- 字段：显示标签*、存储值*（编辑时 disabled）、排序号、状态开关、备注

### 前端 Store

新增 `useDictStore.ts`（Zustand）：
- 缓存常用字典数据（避免重复请求）
- `getDictItems(code)` — 获取指定编码的字典项（先查缓存）
- 供全局使用（表单下拉、表格状态显示等）

## 初始化数据

后端启动时自动创建以下字典（如不存在）：

| dict_code | dict_name | 字典项 |
|---|---|---|
| tender_method | 招标方式 | 公开招标(PUBLIC), 邀请招标(INVITE), 竞争性谈判(NEGOTIATE), 询价(INQUIRY), 单一来源(SINGLE) |
| tender_source | 信息来源 | 政府采购网(GOV), 招标信息网(BID_INFO), 企业直邀(DIRECT), 中介推荐(AGENT), 其他(OTHER) |
| bid_status | 投标状态 | 待评估(PENDING), 已决策-投标(DECIDED_BID), 已决策-放弃(DECIDED_GIVE_UP), 编制中(COMPOSING), 已提交(SUBMITTED), 已开标(OPENED) |
| decision_result | 决策结果 | 通过(PASS), 不通过(REJECT), 待定(PENDING) |
| opening_result | 开标结果 | 中标(WIN), 未中标(LOSE), 废标(INVALID), 流标(ABORTED) |
| doc_type | 标书文档类型 | 技术方案(TECH), 商务报价(COMMERCIAL), 资质文件(QUALIFICATION), 承诺函(COMMITMENT), 其他(OTHER) |
| cert_type | 资质证书类型 | 营业执照(BUSINESS_LICENSE), 资质证书(QUALIFICATION), ISO认证(ISO), 安全生产许可证(SAFETY), 其他(OTHER) |
| urgency | 紧急程度 | 正常(NORMAL), 紧急(URGENT), 特急(CRITICAL) |

## 验收标准

1. 后端 9 个 API 全部可用，curl 测试通过
2. 启动后自动创建 8 个字典和对应字典项
3. 前端数据字典页面正常渲染
4. 左侧点击字典类型 → 右侧显示对应字典项
5. 新增/编辑/删除字典类型和字典项均可操作
6. 编码和存储值编辑时不可修改
7. 删除有字典项的类型时提示拒绝
8. TypeScript 编译无错误
9. Vite 构建成功
