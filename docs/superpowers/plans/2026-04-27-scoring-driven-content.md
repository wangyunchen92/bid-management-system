# 实施计划 — 链路 B：评分项驱动的 AI 内容生成

**日期**：2026-04-27
**关联设计**：`docs/superpowers/specs/2026-04-27-scoring-driven-content-design.md`
**回退点**：commit `cf73cec7`

---

## 决策已确认

| 议题 | 决策 |
|---|---|
| 章节 ↔ 评分项关联 | **多对多** |
| 资料库素材注入 | **生成时实时查** |
| v2 自评 | **不在 v1 范围**，先看反馈再加 |

---

## 一、数据库变更

### 1.1 新表 `bid_scoring_item`

```sql
CREATE TABLE bid_scoring_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id BIGINT NOT NULL,
    category VARCHAR(20) NOT NULL,      -- 技术/商务/价格
    item_name VARCHAR(200) NOT NULL,    -- 评分项名称
    max_score NUMERIC(8, 2),
    criteria TEXT NOT NULL,             -- 评分细则原文
    required_evidence TEXT,             -- AI 推断的需要提供的证据
    linked_chapter_hint VARCHAR(200),   -- AI 推断的最适合放置的章节标题
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME, updated_at DATETIME, is_deleted SMALLINT DEFAULT 0
);
CREATE INDEX ix_bid_scoring_item_project ON bid_scoring_item(project_id);
```

### 1.2 中间表 `bid_section_scoring_item`（多对多）

```sql
CREATE TABLE bid_section_scoring_item (
    section_id BIGINT NOT NULL,
    scoring_item_id BIGINT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME,
    PRIMARY KEY (section_id, scoring_item_id)
);
CREATE INDEX ix_bsi_section ON bid_section_scoring_item(section_id);
CREATE INDEX ix_bsi_scoring ON bid_section_scoring_item(scoring_item_id);
```

> 用中间表而不是 bid_section 的 string 字段，因为多对多 + 后续要查"评分项关联了哪些章节"和"章节关联了哪些评分项"两个方向，关系表更规范。

---

## 二、后端改动

### 2.1 model

| 文件 | 改动 |
|---|---|
| `models/bid.py` | 加 `BidScoringItem` 和 `BidSectionScoringItem` 类 |

### 2.2 schema

| 文件 | 改动 |
|---|---|
| `schemas/bid.py` | 加 `ScoringItemResponse` / `LinkScoringRequest` |

### 2.3 AI 解析 prompt

`tender_ai_parser.py` 第 47-55 行：

```python
"scoring": {
    "method": "评分方式",
    "technical_score": null,
    "commercial_score": null,
    "price_score": null,
    "details": [
      {
        "category": "技术/商务/价格",
        "item": "评分项名称",
        "max_score": null,
        "criteria": "评分标准原文",
        "required_evidence": "需要提供什么证据材料才能拿到这分（如：合同扫描件、设备购置发票、人员证书等）",
        "linked_chapter_hint": "最适合放在哪个章节（标题，如：业绩证明材料、人员配备、整体服务方案）"
      }
    ]
}
```

### 2.4 framework 生成时落库评分项 + 自动关联章节

`bid_framework_service.generate_from_tender` 在创建完所有 BidSection 后：

```python
# 7. 落库评分项 + 自动关联章节
scoring_details = parse_result.get("scoring", {}).get("details", [])
sections_by_title = {s.title: s for s in created_sections}

for sort_idx, item in enumerate(scoring_details):
    scoring_item = BidScoringItem(
        project_id=project_id,
        category=item.get("category", "技术"),
        item_name=item.get("item", ""),
        max_score=item.get("max_score"),
        criteria=item.get("criteria", ""),
        required_evidence=item.get("required_evidence"),
        linked_chapter_hint=item.get("linked_chapter_hint"),
        sort_order=sort_idx,
    )
    db.add(scoring_item)
    await db.flush()

    # 自动关联：根据 linked_chapter_hint 匹配章节
    hint = item.get("linked_chapter_hint", "").strip()
    if hint:
        for title, section in sections_by_title.items():
            if hint in title or title in hint:
                db.add(BidSectionScoringItem(
                    section_id=section.id,
                    scoring_item_id=scoring_item.id,
                ))
                break

await db.commit()
```

### 2.5 新接口

| 路径 | 方法 | 功能 |
|---|---|---|
| `/api/v1/bid/projects/{pid}/scoring-items` | GET | 列项目所有评分项 |
| `/api/v1/bid/sections/{sid}/scoring-items` | GET | 列章节关联的评分项 |
| `/api/v1/bid/sections/{sid}/scoring-items` | PUT | 全量更新章节关联（传 ids 数组） |

放在新文件 `routers/bid_scoring.py` 或合并到 `bid.py`，倾向后者。

### 2.6 AI 生成 prompt 升级

`bid_service.aiGenerateSection`（或对应 service 方法）：

```python
async def ai_generate_section(self, db, section_id, user_id, additional_context=""):
    section = ...
    project = ...

    # 拉评分项
    scoring_items = await self._get_scoring_items_for_section(db, section_id)

    # 拉资料库素材（按章节标题/类型匹配）
    library_snippets = await self._get_library_snippets_for_section(db, section)

    prompt = self._build_section_gen_prompt(section, scoring_items, library_snippets, additional_context)

    # 调 AI 生成（流式）
    ...
```

#### `_get_library_snippets_for_section`

按章节关键词 + 评分项 required_evidence，从 4 个库表里抓 top N：

```python
async def _get_library_snippets_for_section(self, db, section):
    keywords = self._infer_section_keywords(section.title)
    snippets = {"业绩": [], "人员": [], "资质": [], "设备": []}

    if any(k in section.title for k in ["业绩", "成功案例"]) or "业绩" in keywords:
        # 查 lib_achievement
        results = await db.execute(
            select(Achievement).where(Achievement.is_deleted == 0).limit(5)
        )
        snippets["业绩"] = [{"name": a.project_name, "client": a.client_name, "amount": a.amount, "year": a.year} for a in results.scalars()]

    if any(k in section.title for k in ["人员", "团队", "项目组"]):
        results = await db.execute(select(PersonnelCert).where(PersonnelCert.is_deleted == 0).limit(10))
        snippets["人员"] = [{"name": p.person_name, "cert": p.cert_name, "type": p.cert_type} for p in results.scalars()]

    if any(k in section.title for k in ["资质", "证书", "许可"]):
        results = await db.execute(select(Qualification).where(Qualification.is_deleted == 0).limit(10))
        snippets["资质"] = [...]

    if any(k in section.title for k in ["设备", "机器"]):
        results = await db.execute(select(Product).where(Product.is_deleted == 0).limit(10))
        snippets["设备"] = [...]

    return snippets
```

#### `_build_section_gen_prompt`

```python
def _build_section_gen_prompt(self, section, scoring_items, library_snippets, additional_context):
    parts = [
        "你是标书撰写专家。请撰写本章节内容。",
        "",
        f"章节标题：{section.title}",
        "",
    ]

    if scoring_items:
        parts.append("【关联评分项 — 这是拿分关键，请逐条响应】")
        for it in scoring_items:
            parts.append(f"\n- 评分项：{it.item_name}（满分 {it.max_score} 分，类别：{it.category}）")
            parts.append(f"  评分细则：{it.criteria}")
            if it.required_evidence:
                parts.append(f"  需要提供的证据：{it.required_evidence}")

    if any(library_snippets.values()):
        parts.append("\n【企业资料库可用素材 — 请引用作为佐证】")
        for kind, items in library_snippets.items():
            if items:
                parts.append(f"\n{kind}：")
                for it in items:
                    parts.append(f"- {it}")

    parts.extend([
        "",
        "【撰写要求】",
        "1. 直接对照评分细则的每个评分要素逐条响应（如评分细则有'内容完整性'，请明确写'本方案完整覆盖了 ABC...'）",
        "2. 引用上述企业资料素材作为佐证（'近三年我公司承接 XX 项目...'）",
        "3. 数据/数字要具体（不要'丰富经验'，要'承接 X 个同类项目，金额合计 Y 万元'）",
        "4. 输出 markdown，含小标题（## 子节）和列表",
        "",
    ])

    if additional_context:
        parts.append(f"【附加要求】\n{additional_context}\n")

    parts.append("【输出格式】\n直接输出章节正文，不要带'以下是...'引导语。")
    return "\n".join(parts)
```

---

## 三、前端改动

### 3.1 「评分表」Tab（招标信息卡）

`pages/Bid/Workbench/index.tsx`：
- 在招标信息侧栏加 Tab：「招标基本」「评分表」「时间线」
- 「评分表」按 category 分组（技术/商务/价格）展示评分项
- 每行显示：item_name（粗体）+ max_score（颜色徽章）+ criteria（折叠展示）
- 末列：「关联章节」展示已关联章节标题，可点击跳转

### 3.2 章节编辑器加「关联评分项」面板

章节正文上方加一个折叠区：
- 列出已关联评分项（小卡片：item_name + max_score + criteria 简要）
- 「+ 关联评分项」按钮 → 弹出多选 Modal，从项目所有评分项里选
- 「AI 智能生成」按钮（替换现有「AI 生成」）：
  - 调用新 v2 接口
  - prompt 自动带评分项 + 资料库
  - 流式显示

### 3.3 章节列表「关联 X 项 / Y 分」标签

每个章节标题旁显示一个小 Tag：「关联 2 项 / 25 分」（绿色）或「未关联」（灰色）。

---

## 四、实施步骤

### 步骤 1：DB schema + model（30 分钟）
- 新增 BidScoringItem + BidSectionScoringItem 模型
- Schema 类
- 测试 metadata.create_all 在本地能建表

### 步骤 2：AI 解析 prompt 升级（15 分钟）
- tender_ai_parser scoring.details 加 required_evidence + linked_chapter_hint

### 步骤 3：framework 生成落库 + 自动关联（45 分钟）
- 修改 bid_framework_service.generate_from_tender
- 测试一个新项目走完整流程

### 步骤 4：评分项查询接口（20 分钟）
- routers/bid.py 加 3 个端点
- 前端 services/bid.ts 加对应方法

### 步骤 5：AI 生成 prompt 重写（45 分钟）
- _get_library_snippets_for_section
- _build_section_gen_prompt
- 改 aiGenerateSection 流程
- 测试：拿一个章节生成，对比新 prompt 的内容

### 步骤 6：前端「评分表」Tab（45 分钟）
- 招标信息卡片加 Tab
- 评分项分组渲染

### 步骤 7：前端章节关联面板（60 分钟）
- 章节编辑器顶部加面板
- 多选 Modal
- 「关联 X 项」标签

### 步骤 8：本地端到端测试（30 分钟）
- 删除现有项目，重新走全流程
- 验证：评分项落库 / 章节自动关联 / AI 生成带评分项

### 步骤 9：上线（30 分钟）
- rsync backend
- 跑 metadata.create_all 建新表
- rsync frontend dist
- systemctl restart
- smoke test

### 步骤 10：commit + push（10 分钟）
- 5-6 个原子 commit
- 推送

**总计：约 6 小时**

---

## 五、文件清单

| 文件 | 改动 |
|---|---|
| `backend/app/models/bid.py` | + BidScoringItem + BidSectionScoringItem |
| `backend/app/schemas/bid.py` | + ScoringItem schema + Link request |
| `backend/app/services/tender_ai_parser.py` | scoring.details 新增 2 字段 |
| `backend/app/services/bid_framework_service.py` | generate_from_tender 末尾落库评分项 + 自动关联 |
| `backend/app/services/bid_service.py` | + 3 个评分项接口方法 + AI 生成升级 |
| `backend/app/routers/bid.py` | + 3 个评分项端点 |
| `backend/scripts/init_scoring_tables.py` | metadata.create_all 建表 |
| `frontend/src/services/bid.ts` | + scoring API 方法 |
| `frontend/src/types/api.ts` | + ScoringItem 类型 |
| `frontend/src/pages/Bid/Workbench/index.tsx` | 评分表 Tab + 章节关联面板 + 新 AI 生成按钮 |

---

## 六、测试用例

### 6.1 评分项落库

输入：项目 14 重新解析（或新项目走全流程）
预期：
- bid_scoring_item 表里有 N 行（N = AI parse 出的评分项数）
- bid_section_scoring_item 表里有 M 行（自动关联的）
- 至少 70% 评分项关联到了对应章节

### 6.2 AI 生成带评分项

输入：章节"整体服务方案"，关联评分项「服务方案完整性 10 分」
预期：
- 生成内容含评分细则提到的关键点（"完整覆盖"、"针对性"等）
- 至少引用 1 个企业资料库素材

### 6.3 前端关联管理

- 章节列表能看到"关联 X 项"标签
- 章节编辑器侧栏能加/删评分项
- 评分表 Tab 能看到所有评分项 + 关联状态

---

## 七、不做（v2）

- 章节自评（estimated_score）
- 评分项手动编辑（用户改 AI 解析错的项）
- 资料库素材注入失败（库里没数据）时的提示 UX
- 评分项预算与实得分对比图

---

## 八、风险

| 风险 | 缓解 |
|---|---|
| AI 解析不出 required_evidence 字段 | prompt 设计为可空；fallback 用 criteria 文本 |
| 自动关联匹配率低 | 用户可手动改；后续看命中率统计 |
| 资料库为空时 prompt 注入素材为空 | 在 prompt 里说明素材不足时怎么写 |
| 长 prompt 成本上升 | 监控；最坏情况限制 top 3 评分项 + top 3 资料 |
