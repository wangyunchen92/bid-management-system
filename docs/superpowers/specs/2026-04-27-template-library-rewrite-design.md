# 应标函章节切换至模板库驱动 — 设计文档

**日期**：2026-04-27
**作者**：backend-agent + controller
**关联讨论**：链路 A（应标函模板填空）vs 链路 B（评分项内容）的拆分对话
**目标**：移除"AI 抽招标 PDF 模板 → 8 条 markdown 后处理"链路对**应标函类章节**的依赖，改由清洁的知识库模板驱动

---

## 一、背景与问题

### 1.1 当前实现链路

```
PDF → pdfplumber 抽表 + PyMuPDF 抽散文（broken table cells）
    → AI parser（一次大调用）输出 chapters[].template
    → bid_framework_service.generate_from_tender
       └ TEMPLATE 章节：用 AI 抽出的 template
       └ MANUAL 章节：同上
    → _apply_substitutions（占位符替换）
    → _format_template（8 条 markdown 修复规则）
    → BidSection.content（markdown 字符串）
    → 前端 MarkdownContent / TipTap 渲染
```

### 1.2 已发现的脆弱点

| 痛点 | 来源 |
|---|---|
| 表格 cell 含 `\n` 被 markdown 解析器拆散 | pdfplumber 输出未转 `<br>` |
| AI 部分修部分不修，输出不一致 | 一次大调用做太多事 |
| 表格行间空行被当成表格结束 | AI 习惯插段落分隔 |
| 占位符识别要覆盖：花括号 `{}`、中文括号 `（）`、表格空白 cell 三种格式 | 字符串模式匹配 |
| 每来一份新 PDF 都可能暴露新的 markdown 边界情况 | 后处理打补丁式增长 |

`_format_template` 已经有 8 条规则（cell 合并、表格行合并、空行去除、空 cell 填 ____、签章块追加、段落分隔、日期填今天、库附件注入），还在持续打补丁。

### 1.3 核心洞察

**政采应标函类内容（响应函/授权书/承诺函/各类声明）全国都用同一套样板话术**——财政部样板、各地代理机构样板，**只是换项目名/招标人/日期/供应商信息**。

我们已经在 `knowledge_template` 表里维护了清洁版本：

| id | title | 用途 |
|---|---|---|
| 1 | 响应函（竞争性磋商通用模板） | TEMPLATE |
| 2 | 法定代表人授权委托书模板 | TEMPLATE |
| 3 | 主要成交标的承诺函模板 | TEMPLATE |
| 4 | 无重大违法记录声明函模板 | TEMPLATE |
| 5 | 诚信履约承诺函模板 | TEMPLATE |
| 6 | 服务承诺函模板 | TEMPLATE |
| 11 | 法定代表人身份证明书模板 | TEMPLATE |
| 12 | 中小企业声明函模板 | TEMPLATE |

这 8 条恰好覆盖了**当前 STANDARD_FRAMEWORK 中所有 TEMPLATE 类型章节**。完全没必要让 AI 再去 PDF 里抽。

---

## 二、新方案

### 2.1 章节路由策略（三类）

按章节类型走不同链路：

| 类别 | 章节示例 | 链路 |
|---|---|---|
| **A. 标准应标函** | 响应函、授权书、各类声明函、承诺函、身份证明书 | **库模板 + 占位符填值**（v1 范围） |
| **B. 项目特定表单** | 报价表、最后承诺报价表、商务条款偏离表、技术偏离表 | **保留 AI 抽取**（短期）；v2 升级 PDF 覆盖层 |
| **C. AI 撰写方案** | 整体服务方案、质量控制方案、技术方案 | **不变**，TipTap markdown 编辑器 + AI 生成（属于链路 B 评分项驱动的范畴，本设计不动）|

### 2.2 路由判定逻辑

`generate_from_tender` 处理每个章节时：

```python
chapter = {"title": "授权书", "section_type": "TEMPLATE", "template": "..."}

# 1. 标准应标函识别（按章节标题关键词匹配库模板）
matched_lib_template_id = match_standard_letter(chapter["title"])

if matched_lib_template_id:
    # A. 库模板路径：忽略 AI 抽出的 template，直接用库
    content = await fill_library_template(matched_lib_template_id, project)
elif chapter.get("template"):
    # B. AI 抽取路径：保留现有逻辑（_apply_substitutions + _format_template）
    content = await apply_substitutions(chapter["template"], project, section_type)
else:
    # C. 空内容（用户后续 AI 生成或手填）
    content = ""
```

**关键变化**：库模板路径**不调用** `_format_template` 的 8 条 markdown 后处理规则——库模板本来就是清洁的 markdown，不需要修。

### 2.3 标准应标函匹配字典

显式硬编码（不让 AI 二次推断），便于测试和调优：

```python
STANDARD_LETTER_TEMPLATES = {
    # 章节标题关键词 → 库模板 id
    ("响应函", "磋商响应函", "投标函"): 1,
    ("授权委托书", "授权书", "法人授权"): 2,
    ("主要成交标的承诺", "成交标的承诺函"): 3,
    ("无重大违法", "违法记录声明", "不良信用声明"): 4,
    ("诚信履约承诺",): 5,
    ("服务承诺函", "服务承诺"): 6,
    ("法定代表人身份证明", "身份证明书", "法人身份证明"): 11,
    ("中小企业声明",): 12,
}

def match_standard_letter(chapter_title: str) -> Optional[int]:
    title = chapter_title.strip()
    for keywords, template_id in STANDARD_LETTER_TEMPLATES.items():
        if any(kw in title for kw in keywords):
            return template_id
    return None
```

匹配是 **章节标题关键词包含**，不依赖 tags（tag 匹配易错）。

### 2.4 占位符替换（与现有 _apply_substitutions 保持兼容）

库模板里只用花括号占位符：
- `{项目名称}` `{招标编号}` `{招标单位}`（来自 tender 表）
- `{公司名称}` `{法定代表人}` `{统一社会信用代码}` 等（来自 settings.COMPANY_*）
- `{日期}` 自动填今天

**不再需要**：
- 中文括号 `（供应商名称）` 替换（库模板不写这种）
- 表格空白 cell 自动填（库模板不留空 cell）
- `____` 占位符填库（库模板必要的留空保留 `____` 给用户）

### 2.5 AI prompt 简化

现行 `tender_ai_parser.parse` 让 AI 给每个章节抽 `template`。新方案：**只对非标准应标函章节抽 template**。

prompt 改为：
> chapters 中的 template 字段：找招标文件中"响应文件格式""附件"等部分，**仅对项目特定章节抽出**模板原文（如：报价表、商务/技术偏离表、特定声明表）。**对响应函、授权书、声明函、承诺函、身份证明书等通用应标函，template 字段统一返回空字符串**——这些章节系统会从知识库匹配标准模板，不需要从招标文件里抽。

效果：
- AI 输出 token 减少 ~40%（应标函类的样板话术不再重复输出）
- 解析时间预计从 70-80s 降到 50-60s

---

## 三、数据 / 模型变更

### 3.1 数据库

**无需变更**。`knowledge_template` 表已有，`bid_section.content` 仍是 markdown 字符串。

### 3.2 库模板内容审计

需要逐一检查 8 个库模板：

| 检查项 | 期望 |
|---|---|
| 不含旧项目名（"安徽博物院..."等硬编码）| ✅ |
| 占位符统一为 `{xxx}` 花括号格式 | ✅ |
| 表格符合 GFM（cell 内换行用 `<br>`）| ✅ |
| `____` 留给用户填的字段（如金额、签字）保留 | ✅ |
| 末尾有签章块（"供应商电子签章：____"+ 日期占位）| ✅ |

实施前会输出一份审计清单（哪些需要修），由用户确认后批量修。

---

## 四、代码变更清单

| 文件 | 改动 |
|---|---|
| `bid_framework_service.py` | 新增 `STANDARD_LETTER_TEMPLATES` 字典 + `match_standard_letter()` ；`generate_from_tender` 路由分发 |
| `bid_framework_service.py` | 库模板路径走 `_apply_substitutions` 但**跳过** `_format_template` 的 markdown 修复部分 |
| `tender_ai_parser.py` | prompt 改为：标准应标函章节 template 留空 |
| `_format_template` | 砍掉 8b（中文括号填空）、8a-2（空 cell 填 ____）、8c（签章块追加）—— 这些规则只为应标函类设计的，去掉后这些规则只对项目特定表单生效 |

**预计删除**：~120 行后处理代码（来自 `_format_template`）。
**预计新增**：~50 行（路由 + 字典）。
**净减少**：~70 行 + 一类持续打补丁的负担。

### 4.1 拆分 `_apply_substitutions` 与 `_format_template`

为了让两条路径清晰：

```python
async def _apply_substitutions(content, project, section_type):
    """通用占位符替换（花括号 + 旧项目文本 + 日期）—— 库模板和 AI 抽取都走"""
    # 保留：旧项目文本替换、{占位符}、签章日期、库附件注入
    # 删除：中文括号填空、表格空 cell 填空、签章块追加
    return content

def _normalize_ai_extracted_markdown(content, section_type):
    """仅对 AI 抽出的 markdown 做修复（cell 跨行合并、表格空行去除、表格规整）"""
    # 保留：8-pre _join_broken_table_rows、8-pre2 表格行间空行去除、8a 表格列对齐
    # 这条只对项目特定表单（报价表/偏离表）生效
    return content
```

新流程：

```
库模板路径：fill_library_template → _apply_substitutions（精简版）→ 入库
AI 抽取路径：AI extract → _apply_substitutions（精简版）→ _normalize_ai_extracted_markdown → 入库
```

---

## 五、前端影响

**最小**。`MarkdownContent` 和 `RichTextEditor` 都不需要改。

唯一影响：
- 应标函章节渲染会更稳定（库模板已经是干净 markdown）
- 报价表/偏离表仍走 AI 抽取，仍依赖 `_normalize_ai_extracted_markdown` 修复（这部分代码保留）

---

## 六、迁移与兼容

### 6.1 老项目（如线上项目 13）

策略：**不主动迁移**。已生成的章节按 AI 抽取流程产出，已经修过 8 轮，留着不动。

### 6.2 新项目

走新流程，应标函章节用库模板，预计零 markdown 渲染问题。

### 6.3 用户感知

| 场景 | 体验 |
|---|---|
| 老项目打开 | 不变 |
| 新项目「一键填入招标信息」| 应标函章节内容更整洁（库模板）；报价表/偏离表与之前类似 |
| 解析速度 | 略快（AI 输出少了应标函话术）|

---

## 七、不在本设计范围内（v2 候选）

| 议题 | 备注 |
|---|---|
| 报价表 / 偏离表也切到库模板 | 这些有 PDF 项目特定字段，要么走 PDF 覆盖层，要么用半结构化 schema |
| PDF 覆盖层方案 | 上一轮你提的方向；做完链路 A v1 评估是否启动 |
| 评分项驱动章节生成（链路 B）| 单独设计文档 |
| AI 自动判别"这个章节是不是标准应标函" | 当前用关键词字典够用；后续看不命中率再决定是否加 AI 二次判别 |

---

## 八、验收标准

1. ✅ `STANDARD_LETTER_TEMPLATES` 8 个标题关键词集对应正确 `knowledge_template.id`
2. ✅ 新建项目走「一键填入招标信息」后，应标函章节 content 与库模板填值后一致（不含 PDF 抽出的杂质）
3. ✅ 应标函章节渲染**0 个** markdown 表格 bug（无断行、无空行打散表格）
4. ✅ 报价表/偏离表仍能正常生成（AI 抽取路径未受影响）
5. ✅ 老项目章节内容不变
6. ✅ AI 解析时间下降 ≥ 15%（粗略指标，因 token 输出减少）
7. ✅ `_format_template` 代码量 < 当前 50%

---

## 九、实施步骤（待确认后落到 plan）

1. **库模板审计**：输出 8 个模板的检查报告，用户确认是否要清理
2. **`STANDARD_LETTER_TEMPLATES` 字典**：定稿关键词集
3. **代码改造**：路由分发 + `_apply_substitutions` 精简 + `_normalize_ai_extracted_markdown` 抽出
4. **AI prompt 改造**：应标函章节 template 留空
5. **本地验证**：用现有招标 PDF 走新流程，对比章节内容
6. **测试用例**：5 个应标函章节 + 2 个项目特定章节的对比测试
7. **部署 + 灰度**：新项目走新流程；老项目维持不动

---

## 十、风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 章节标题关键词命中失败 | 应标函章节走 AI 抽取的旧路径 | 字典持续扩充；fallback 逻辑保留 |
| 库模板不全或质量差 | 部分章节内容不准 | 审计步骤先做，确认后再改 |
| AI 输出格式倒退（不再返回 template）| 老的 chapters 解析逻辑要兼容 template 缺失 | 已经兼容（template 留空时直接落 content="")|
