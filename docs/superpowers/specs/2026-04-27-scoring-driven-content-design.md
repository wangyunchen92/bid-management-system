# 链路 B：评分项驱动的内容生成 — 设计文档

**日期**：2026-04-27
**关联**：链路 A 已完成（应标函库模板化）；本文设计**评分项驱动**的方案/响应类章节生成
**目标**：把 AI_GENERATE 类章节（整体服务方案 / 技术方案 / 质量措施 / 服务承诺等）的生成逻辑，从"按固定章节标题写"转为"**按招标评分细则有针对性地写**"，让用户每一节都瞄准拿分

---

## 一、背景

### 1.1 当前痛点

链路 A 解决了应标函类章节（响应函/授权书/各类声明 + 报价表）的生成。剩下的 AI_GENERATE 类章节有 ~10 个：

| 章节 | 当前生成方式 |
|---|---|
| 整体服务方案 | 用户点「AI 生成」按钮，prompt 是泛化的"撰写整体服务方案"|
| 印刷工艺及色彩管理方案 | 同上 |
| 质量控制及保证措施 | 同上 |
| 项目实施进度计划 | 同上 |
| 包装运输配送方案 | 同上 |
| 保密措施 | 同上 |
| 绿色印刷及环保措施 | 同上 |
| 安全生产方案 | 同上 |
| 售后服务方案 | 同上 |
| 服务承诺（细化） | 同上 |

**核心问题**：
1. AI 不知道这次招标对这一节**具体打多少分**、**评分细则要点是什么**
2. AI 不知道公司有什么**业绩/人员/资质**可以"喂"进去对应评分项
3. 写完没有"**这一节预计能拿多少分**"的反馈

而招标文件里每一份的**评分细则**都明文写着拿分要点，这是商务人员中标率的核心信息。

### 1.2 真实政采评分表样例

```
技术资信分（70 分）
├─ 供应商业绩：每提供 1 项学生证或学生手册等印刷服务业绩得 5 分，满分 20 分
├─ 业绩反馈：业主评价良好/满意每个加 5 分，满分 10 分
├─ 服务方案完整性：内容全面有针对性 10 分；基本完整 5 分；不可行 0 分（满分 10 分）
├─ 样品：材质规格符合性 0-4 分；印刷工艺质量 0-4 分（满分 8 分）
├─ 人员配备：项目经理资质相关 ≥3 年 5 分；其他人员 5 分（满分 10 分）
└─ 设备配备：印刷机/装订机数量 8-12 分（满分 12 分）

商务分（30 分）
├─ 报价：基准价偏离百分比（满分 30 分）

合计 100 分
```

每一项都明确告诉你"提供 XX 得 X 分"。AI 写"整体服务方案"时如果**显式带这些信息**，能写得更有的放矢。

---

## 二、当前数据基础

`tender_ai_parser` 已经在解析中输出 `scoring.details`：

```json
{
  "scoring": {
    "method": "综合评分法",
    "technical_score": 70,
    "commercial_score": 30,
    "price_score": null,
    "details": [
      {
        "category": "技术",
        "item": "供应商业绩",
        "max_score": 20,
        "criteria": "每提供 1 项学生证或学生手册等印刷服务业绩得 5 分，满分 20 分"
      },
      ...
    ]
  }
}
```

**当前局限**：
- `details` 只有 4 个字段，缺少结构化的"需要提供的证据"
- 不和章节关联，AI 生成时拿不到
- 前端没展示评分表

---

## 三、新方案

### 3.1 核心理念

```
招标文件解析（已有）
  ↓ 输出 scoring.details
评分项落库（新）→ bid_scoring_item 表
  ↓
章节关联评分项（新）→ bid_section.scoring_item_ids
  ↓
AI 生成章节内容（增强）
  ├─ prompt 注入：评分细则、满分、关联企业资料库证据
  └─ 输出后做粗略自评（v2）
  ↓
用户编辑/确认 → 入库
```

### 3.2 数据模型变更

#### 新表 `bid_scoring_item`

```python
class BidScoringItem(BaseModel):
    __tablename__ = "bid_scoring_item"

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # 技术/商务/价格
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    max_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    criteria: Mapped[str] = mapped_column(Text, nullable=False)         # 评分细则原文
    required_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI 推断的证据要求
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

`required_evidence` 由 AI 解析时一并推断（如"提供合同扫描件"、"提供设备购置发票"等）。

#### `bid_section` 加字段

```python
scoring_item_ids: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
# 逗号分隔的 ScoringItem id 列表，一个章节可关联多个评分项
self_eval_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
self_eval_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

### 3.3 AI 解析增强

`tender_ai_parser` prompt 的 `scoring.details` schema 加 `required_evidence`：

```json
{
  "category": "技术",
  "item": "供应商业绩",
  "max_score": 20,
  "criteria": "每提供 1 项学生证或学生手册等印刷服务业绩得 5 分，满分 20 分",
  "required_evidence": "近 3 年学生证/学生手册等同类印刷服务的合同扫描件 + 业主良好/满意评价",
  "linked_chapter_hint": "业绩证明材料"
}
```

`linked_chapter_hint` 是 AI 给的"这条评分项最适合放在哪个章节"的提示，便于自动关联。

### 3.4 章节-评分项自动关联

招标文件解析完成后，跑一次匹配：

| 评分项 item | 自动关联章节 |
|---|---|
| 供应商业绩 | 业绩证明材料 |
| 业绩反馈 | 业绩证明材料 |
| 服务方案完整性 | 整体服务方案 |
| 印刷工艺质量 | 印刷工艺及色彩管理方案 |
| 人员配备 | 人员配备 |
| 设备配备 | 设备配备 |
| 售后服务承诺 | 售后服务方案 |
| 报价 | 报价表 |

匹配逻辑：用关键词（含关键词字典）+ AI 兜底（必要时）。**v1 用关键词字典+章节 title 模糊匹配**，命中率应该 70-80%；后续看效果。

### 3.5 AI 生成 prompt 增强

当前 `aiGenerateSection` prompt：
```
你是标书撰写专家。请撰写本章节内容。
章节标题：{title}
招标要求：{tender_requirements}
附加要求：{additional_context}
```

新版 prompt：
```
你是标书撰写专家。请撰写本章节内容。

章节标题：{title}

【关联评分项 — 这是拿分关键】
{对每个 ScoringItem：}
- 评分项：{item_name}（满分 {max_score} 分，类别：{category}）
  评分细则：{criteria}
  需要提供的证据：{required_evidence}

【企业资料库可用素材】
{从 lib_qualification/lib_personnel_cert/lib_achievement/lib_product 拉取与本章节相关的项目：}
- 业绩：{相关 N 个，含项目名称/客户/规模/年份}
- 人员：{相关 N 个，含姓名/职务/证书}
- 资质：{相关 N 个}
- 设备：{相关 N 个}

【撰写要求】
1. 直接对照评分细则的每个评分要素逐条响应
2. 引用上述企业资料素材作为佐证（"近三年我公司承接 XX 项目..."）
3. 数据/数字要具体（不要"丰富经验"，要"承接 X 个同类项目"）
4. 输出 markdown，含小标题和列表

【输出格式】
直接输出章节正文，不要带"以下是..."这种引导语。
```

### 3.6 章节自评（v2，本设计先列规范）

生成后再调一次 AI 做粗略自评：

```
基于以下章节内容和评分细则，预估能拿多少分：

【章节内容】
{generated_content}

【评分细则】
{criteria}（满分 {max_score} 分）

输出 JSON：
{
  "estimated_score": 8.5,  // 预计得分
  "max_score": 10,
  "breakdown": [
    {"criterion": "内容全面性", "scored": 4, "max": 4, "comment": "覆盖完整"},
    {"criterion": "针对性可行性", "scored": 3.5, "max": 4, "comment": "缺少具体时间节点"},
    {"criterion": "数据具体性", "scored": 1, "max": 2, "comment": "建议补具体数字"}
  ],
  "missing_evidence": ["项目实施时间节点"],
  "improvement_tips": "建议补充第二季度具体里程碑"
}
```

**v1 不做**，v2 加。

---

## 四、前端变更

### 4.1 招标信息卡片新增「评分表」Tab

招标文件解析完进入项目工作台后，已有「招标信息」卡片显示 basic_info / timeline。
新加一个 Tab「评分表」展示评分项树：
- 按 category（技术/商务/价格）分组
- 显示 max_score 总和（如"技术分 70/100"）
- 每条展示：item_name、max_score、criteria
- 「关联章节」列：显示已关联的章节 title，点击跳转

### 4.2 章节编辑器加「评分项」侧栏

打开任一 AI_GENERATE 章节，左侧/右侧加一个面板：
- 显示已关联的评分项（item_name + criteria 摘要 + max_score）
- 「+ 关联其他评分项」按钮 → 弹出评分项多选
- 「AI 智能生成」按钮：调新版 prompt（带评分项 + 资料库素材）

### 4.3 章节列表加「关联评分」标签

每个章节标题旁显示"关联 X 项 / 共 Y 分"标签。

---

## 五、API 变更

| 端点 | 用途 |
|---|---|
| `GET /api/v1/bid/projects/{id}/scoring-items` | 列项目所有评分项 |
| `POST /api/v1/bid/sections/{id}/link-scoring` | 关联章节↔评分项（多选） |
| `POST /api/v1/bid/sections/{id}/ai-generate-v2` | 新版 AI 生成（自动注入评分项+资料库） |
| ~~`POST /api/v1/bid/sections/{id}/self-evaluate`~~ | v2 |

---

## 六、实施分期

### v1（本设计落地范围，约 2-3 天）

1. **数据库**
   - 新表 `bid_scoring_item`
   - `bid_section` 加 `scoring_item_ids` 字段
2. **后端**
   - `tender_ai_parser` prompt 加 `required_evidence` + `linked_chapter_hint`
   - `bid_framework_service.generate_from_tender` 后追加：从 parse_result.scoring.details 落库评分项 + 自动关联章节
   - `scoring_item_service.list/link/unlink` 服务
   - `aiGenerateSection` 升级：注入评分项 + 资料库素材到 prompt
3. **前端**
   - 招标信息卡片加「评分表」Tab
   - 章节编辑器加评分项面板
   - 章节列表加"关联 X 项"标签

### v2（不在本设计范围）

- 章节自评（estimated_score）
- 评分项-章节自动关联失败时的 AI 兜底
- 评分项编辑（用户手动调整 AI 解析错的评分项）

---

## 七、对现有项目的兼容

老项目（项目 9/14 等）：
- 不主动迁移
- 重新「一键填入招标信息」时会触发新流程，落库评分项

老的 AI 生成按钮仍可用（不带评分项注入）；新章节有关联评分项时会自动用新 prompt。

---

## 八、风险

| 风险 | 缓解 |
|---|---|
| AI 自动关联章节命中率低 | 用户可手动改关联；v2 加 AI 兜底 |
| 评分项解析不准（遗漏/拆错） | 用户能手动改（v2 评分项编辑功能） |
| 资料库素材不够（业绩太少）| AI prompt 里说明素材不足时如何写（"我公司虽业绩较少，但..."）|
| 评分项 prompt 让 token 用量翻倍 | 监控；必要时只注入 top 3 关联评分项 |

---

## 九、决策点（待你拍板）

1. **章节 ↔ 评分项关联是否多对多**？我设计的是多对多（一个章节可关联多个评分项，一个评分项可被多个章节引用）。简单点的话改成多对一（一个章节关联一个主评分项）。
2. **资料库注入是否在生成时实时查**？或者预先做"章节×资料"映射（用户配置）？v1 实时查更简单，但每次生成多查 4 个表。
3. **v2 自评是否值得做**？这是产品差异化点，但工作量也大。建议 v1 跑通再决定。
