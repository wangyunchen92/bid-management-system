# AI 标书检测（A 版）设计文档

## 概述

将现有的"废标检查"功能升级为结构化的"标书检测"功能。核心改造：从 AI 单次笼统检查，升级为**规则预检 + AI 逐类检测**双层架构，检测结果持久化，支持历史查看。

**目标**：减少废标概率，让用户在提交标书前发现问题并修复。

**定位**：当前作为标书系统内置功能，后续 B 版将独立为可对外服务的检测引擎。

---

## 检测流程

```
用户点击「标书检测」按钮
        ↓
第一层：规则预检（即时，不调 AI，<1秒）
├─ 空章节检查：LIBRARY/AI_GENERATE/TEMPLATE 类型章节内容是否为空
├─ 字数不足检查：技术方案类章节 < 500 字判定 WARNING
├─ 签章落款检查：TEMPLATE 章节是否包含"盖章""签章"关键词
├─ 报价表检查：MANUAL 类型章节是否有内容
└─ 附件完整性：LIBRARY 章节引用的附件文件是否存在
        ↓
第二层：AI 逐类检测（5 轮独立 AI 调用，SSE 流式推送进度）
├─ 资格条件符合性：资质、业绩、人员、财务是否满足招标要求
├─ 评分项覆盖度：招标评分标准中的每个得分项是否在标书中有响应
├─ 技术要求响应度：技术参数、服务要求是否逐条响应
├─ 商务条款偏离风险：偏离表中是否有实质性偏离导致废标
└─ 格式合规性：份数、装订、密封、页码、签章等格式要求
        ↓
合并结果 → 计算综合得分 → 保存到数据库 → 展示检测报告
```

### 得分计算规则

- 规则预检：每条 FAIL 扣 5 分，每条 WARNING 扣 2 分，从 100 分起扣
- AI 检测：5 个类别各 20 分满分，AI 返回每类得分
- 综合得分 = 规则预检得分（40%权重）+ AI 检测得分（60%权重）
- 总分 >= 80：PASS，60-79：WARNING，< 60：FAIL

---

## 数据模型

### 新增表：`bid_check_report`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGINT PK | 主键 |
| project_id | BIGINT NOT NULL | 关联 bid_project.id |
| total_score | INT | 综合得分 0-100 |
| status | VARCHAR(20) | PASS / WARNING / FAIL |
| rule_score | INT | 规则预检得分 0-100 |
| ai_score | INT | AI 检测得分 0-100 |
| rule_items | TEXT (JSON) | 规则预检结果数组 |
| ai_items | TEXT (JSON) | AI 检测结果数组 |
| summary | TEXT | AI 一句话总评 |
| created_at | DATETIME | 检测时间 |
| created_by | BIGINT | 检测人 |
| is_deleted | INT DEFAULT 0 | 软删除 |

### 检查项结构（rule_items 和 ai_items 中每条的 JSON 结构）

```json
{
  "category": "资格条件",
  "check_name": "营业执照有效期检查",
  "status": "PASS",
  "source": "招标文件要求：供应商须具备有效营业执照",
  "detail": "营业执照有效期至2032年02月05日，满足要求",
  "suggestion": null,
  "section_title": "企业资质证明"
}
```

字段说明：
- `category`：检查类别（规则预检 / 资格条件 / 评分覆盖 / 技术响应 / 商务风险 / 格式合规）
- `check_name`：检查项名称
- `status`：PASS / WARNING / FAIL
- `source`：检查依据（招标文件原文引用）
- `detail`：检查结果说明
- `suggestion`：改进建议（PASS 时为 null）
- `section_title`：关联的标书章节标题（可选）

---

## API 设计

### POST `/api/v1/bid/projects/{project_id}/detect`

发起标书检测，SSE 流式返回进度。

**SSE 事件流格式：**

```
data: {"type": "rule_start"}
data: {"type": "rule_item", "item": {...}}
data: {"type": "rule_done", "rule_score": 85, "count": 8}
data: {"type": "ai_start", "category": "资格条件", "current": 1, "total": 5}
data: {"type": "ai_item", "item": {...}}
data: {"type": "ai_category_done", "category": "资格条件", "score": 18}
data: {"type": "ai_start", "category": "评分覆盖", "current": 2, "total": 5}
...
data: {"type": "done", "report_id": 123, "total_score": 78, "status": "WARNING"}
```

### GET `/api/v1/bid/projects/{project_id}/detect/reports`

获取历史检测报告列表。

**响应：**
```json
{
  "code": 200,
  "data": [
    {
      "id": 123,
      "total_score": 78,
      "status": "WARNING",
      "summary": "整体基本合规，但缺少财务证明材料",
      "created_at": "2026-04-16T10:30:00"
    }
  ]
}
```

### GET `/api/v1/bid/projects/{project_id}/detect/reports/{report_id}`

获取单份检测报告详情。

**响应：**
```json
{
  "code": 200,
  "data": {
    "id": 123,
    "project_id": 9,
    "total_score": 78,
    "status": "WARNING",
    "rule_score": 85,
    "ai_score": 73,
    "rule_items": [...],
    "ai_items": [...],
    "summary": "...",
    "created_at": "..."
  }
}
```

### 保留 POST `/api/v1/bid/projects/{project_id}/check`

旧接口保留兼容，内部调用新逻辑但不保存报告、不走 SSE。

---

## 后端架构

### 文件结构

```
backend/app/
├── models/bid_check.py          # BidCheckReport 模型（新增）
├── schemas/bid_check.py         # 检测相关 Schema（新增）
├── services/
│   ├── bid_detect_service.py    # 检测服务（新增）
│   │   ├── run_rule_checks()    # 规则预检
│   │   ├── run_ai_checks()     # AI 逐类检测
│   │   └── save_report()       # 保存报告
│   └── bid_ai_service.py       # 现有，check_bid_compliance 保留兼容
└── routers/bid_detect.py        # 检测路由（新增，挂载到 /api/v1/bid/）
```

### 规则预检实现 `run_rule_checks()`

不调 AI，直接查数据库和章节内容：

| 检查项 | 规则 | 状态判定 |
|---|---|---|
| 空章节 | content 为空或 NULL | FAIL（TEMPLATE/LIBRARY），WARNING（AI_GENERATE） |
| 字数不足 | AI_GENERATE 章节 content 长度 < 500 | WARNING |
| 签章缺失 | TEMPLATE 章节不含"盖章""签章""签字" | WARNING |
| 报价未填 | MANUAL 章节（报价表）内容为空 | FAIL |
| 附件缺失 | content 含 `[附件:path:name]`，但文件不存在 | FAIL |

### AI 逐类检测实现 `run_ai_checks()`

每个类别独立调用 AI，传入该类别相关的章节内容 + 招标要求的对应部分：

| 类别 | 传入的招标要求 | 传入的标书章节 |
|---|---|---|
| 资格条件 | parse_result.qualification | 资质证明、业绩、人员、财务 |
| 评分覆盖 | parse_result.scoring | 所有章节标题 + 内容摘要 |
| 技术响应 | parse_result.bid_document_requirements | 技术方案类章节全文 |
| 商务风险 | parse_result.basic_info + 商务条款 | 偏离表、报价表 |
| 格式合规 | parse_result.bid_document_requirements.format | 全部章节结构 |

每轮 AI 调用的 prompt 模板：

```
你是政府采购标书合规性检测专家。

当前检测类别：{category}

招标文件要求：
{requirements}

标书对应内容：
{bid_content}

请逐条检查标书是否满足招标要求，返回 JSON 数组：
[
  {
    "check_name": "检查项名称",
    "status": "PASS/WARNING/FAIL",
    "source": "招标文件原文要求（引用）",
    "detail": "检查结果",
    "suggestion": "改进建议（PASS时为null）"
  }
]

检查原则：
1. 每条必须引用招标文件原文作为依据
2. FAIL = 可能导致废标的硬伤
3. WARNING = 有风险但不一定废标
4. PASS = 明确满足要求
5. 宁严勿松，有疑问判 WARNING
```

AI 配置：temperature=0.1，max_tokens=4096。

---

## 前端设计

### 按钮

工作台顶部工具栏，将原「废标检查」按钮改为「标书检测」，图标不变（SafetyCertificateOutlined），颜色保持橙色。

### 检测流程 UI

点击后不再弹输入 Modal（招标要求从已解析的招标文件自动获取），直接开始检测：

1. 打开右侧 Drawer（宽度 720px）
2. 显示进度：规则预检 → 资格条件 → 评分覆盖 → 技术响应 → 商务风险 → 格式合规
3. 每完成一步，实时显示该步骤的检查结果
4. 全部完成后展示完整报告

### 报告展示

Drawer 内容分为两部分：

**顶部：总览卡片**
- 左：环形得分（颜色同现在：绿>=80，橙60-79，红<60）
- 中：PASS/WARNING/FAIL 统计条（如：✅ 12 ⚠️ 3 ❌ 2）
- 右：一句话总评

**下方：分类 Tab**

| Tab | 内容 |
|---|---|
| 全部 | 所有检查项按 FAIL → WARNING → PASS 排序 |
| 规则预检 | 规则检查结果 |
| 资格条件 | AI 检测的资格类条目 |
| 评分覆盖 | AI 检测的评分覆盖 |
| 技术响应 | AI 检测的技术响应 |
| 商务风险 | AI 检测的商务偏离 |
| 格式合规 | AI 检测的格式要求 |

每个 Tab 内的条目展示：
```
[状态图标] 检查项名称
  依据：招标文件原文引用...
  结果：检查结果说明...
  建议：改进建议...（仅 WARNING/FAIL 显示）
```

**底部：历史记录**
- 折叠面板，点击展开历史检测列表
- 每条显示：时间 + 得分 + 状态，点击切换查看

### 文件变更

```
frontend/src/
├── services/bid.ts              # 新增 detect 相关 API 调用
├── constants/api.ts             # 新增 DETECT 相关常量
└── pages/Bid/Workbench/index.tsx # 替换废标检查相关状态和 UI
```

---

## 兼容性

- 旧 `/check` 接口保留，内部复用新的检测逻辑但不持久化
- 前端废标检查按钮替换为标书检测按钮
- 数据库新增 `bid_check_report` 表，不影响现有表

---

## 不做的事情（B 版再考虑）

- 独立的检测页面（上传招标文件+标书文件）
- 规则引擎配置界面
- 检测报告导出 PDF/Word
- 多企业/多用户计费
- 自定义检查规则
