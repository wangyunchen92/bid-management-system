# 实施计划 — 方案 A：分子主题多轮生成

**日期**：2026-05-07
**分支**：`feature/multi-turn-generation`
**关联设计**：`docs/superpowers/specs/2026-05-07-multi-turn-section-generation-design.md`

---

## 一、Step-by-step

### Step 1：写测试脚本（TDD 基线，30 分钟）

**新文件**：`backend/scripts/test_multi_turn_generation.py`

5 个测试 T1-T5，跑真实生成（成本 ~¥0.5），覆盖：

```python
T1: 多轮路径触发  → 生成"服务方案"章节，输出 ≥ 8 个 ## 标题
T2: 单节字数      → 平均 ≥ 800 字
T3: 整章字数      → ≥ 7000 字
T4: 量化指标密度  → ≥ 50 处带数字+单位
T5: 章节连贯性    → 无重复段（同一句话不在两个 ## 出现）

辅助 (skip 类，不强制):
T0a: SECTION_CHECKLIST 命中且 prompt 含子主题 hint
T0b: SSE progress 事件 ≥ 8 个
```

测试设计为可重复运行（不需要每次都调 AI，可加 `--mock` 跳过实际生成只测 prompt 拼装）。

### Step 2：实施核心逻辑（45 分钟）

**文件**：`backend/app/services/bid_ai_service.py`

#### 2.1 入口路由
`generate_section_content_stream` 改造成路由：

```python
async def generate_section_content_stream(self, db, section_id, ...):
    section = await self._fetch_section(db, section_id)
    checklist = self._section_title_to_checklist(section.title)
    if checklist and len(checklist) >= 3:
        async for evt in self._multi_turn_section_stream(db, section, checklist, ...):
            yield evt
    else:
        async for evt in self._single_turn_section_stream(db, section, ...):
            yield evt  # 原有逻辑保留作 fallback
```

#### 2.2 多轮主流程

```python
async def _multi_turn_section_stream(
    self, db, section, checklist, *, tender_requirements=None, additional_context=None
):
    # 1. 共享上下文（一次性）
    company_info = await self._get_company_info(db)
    tender_req = await self._get_tender_requirements(db, section.project_id) \
                 if not tender_requirements else f"【招标要求】\n{tender_requirements}"
    scoring_block = await self._get_scoring_items_for_section(db, section.id)

    # 2. 累加生成
    written_summaries: list[tuple[str, str]] = []  # [(标题, 末段100字), ...]

    for idx, item in enumerate(checklist):
        subtopic_title, subtopic_hint = self._parse_checklist_item(item)

        # 进度事件
        yield {"progress": {
            "current": idx + 1, "total": len(checklist),
            "subtopic": subtopic_title,
        }}

        # 子主题级 RAG 查询
        rag_query = f"{section.title} - {subtopic_title} {subtopic_hint}"
        rag_ref = await self._get_knowledge_reference(db, rag_query)

        # 拼 prev_summary
        prev_summary = self._format_prev_summary(written_summaries)

        # 子主题 prompt
        prompt = self._build_subtopic_prompt(
            section_title=section.title,
            subtopic_title=subtopic_title,
            subtopic_hint=subtopic_hint,
            rag_ref=rag_ref,
            tender_req=tender_req,
            company_info=company_info,
            scoring_block=scoring_block,
            prev_summary=prev_summary,
            additional_context=additional_context,
        )

        # 流式调用
        section_buffer = []
        try:
            client = self._get_client()
            stream = client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": "你是标书撰写专家，严格按子主题深度展开当前节，不允许写其他子主题。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0.4,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    section_buffer.append(text)
                    yield {"content": text}
        except Exception as e:
            err_text = f"\n\n## {subtopic_title}\n\n（本节生成失败：{e}，请重新生成此节）\n\n"
            yield {"content": err_text}
            section_buffer = [err_text]

        # 累加到 written
        full_section = "".join(section_buffer)
        tail = full_section.strip()[-100:] if full_section.strip() else ""
        written_summaries.append((subtopic_title, tail))

        yield {"section_done": {
            "subtopic": subtopic_title,
            "word_count": len(full_section),
        }}
```

#### 2.3 辅助函数

```python
def _parse_checklist_item(self, item: str) -> tuple[str, str]:
    """从 'X、xxx（hint）' 中切出 标题 / hint"""
    if "（" in item:
        idx = item.index("（")
        return item[:idx].strip(), item[idx:].strip()
    return item.strip(), ""

def _format_prev_summary(self, written: list) -> str:
    if not written:
        return ""
    lines = ["【已写章节回顾】（保证当前节与前面衔接、不重复）"]
    for title, tail in written:
        snippet = tail.replace("\n", " ")[-80:]
        lines.append(f"- {title} ... {snippet}")
    return "\n".join(lines)

def _build_subtopic_prompt(self, section_title, subtopic_title, subtopic_hint,
                            rag_ref, tender_req, company_info, scoring_block,
                            prev_summary, additional_context) -> str:
    parts = [
        f"你是标书撰写专家，正在分子主题深度展开「{section_title}」章节。",
        f"当前要写的子主题是【{subtopic_title}】。",
    ]
    if prev_summary:
        parts.append(f"\n{prev_summary}\n")
    if rag_ref:
        parts.append(f"\n{rag_ref}\n")
    if tender_req:
        parts.append(f"\n{tender_req}\n")
    if company_info:
        parts.append(f"\n{company_info}\n")
    if scoring_block:
        parts.append(f"\n{scoring_block}\n")
    if additional_context:
        parts.append(f"\n额外要求：\n{additional_context}\n")

    parts.append(f"""
【本节硬性要求（不达标视为低质量）】
1. 严格写当前子主题：{subtopic_title}
   {subtopic_hint}
2. 篇幅 800-1500 字（这是单节，不是整章）
3. 三级 markdown 结构：## {subtopic_title} → ### x.1 / ### x.2 → （1）（2）（3） 编号清单
4. 至少 5 处量化指标（数字+单位，如 ≤0.2mm / 7×24h / 22-25℃ / 99.5%），不允许"较高""丰富""完善"等空话
5. 用印刷行业术语（晒版/套印/网点/油墨密度/烫银/哑膜/卡板/CMYK 等）
6. 引用企业素材时具体到「项目名（甲方+金额万元+年份）」格式
7. 模仿【行业写作风格参考】的密度和层级，但不照抄文字
8. 直接以 ## {subtopic_title} 开头，**只写本节**，不要写其他子主题
9. 不带"以下是..."引导语
""")
    return "\n".join(parts)
```

### Step 3：本地端到端测试（30 分钟）

```bash
cd backend
python3 scripts/test_multi_turn_generation.py
# 预期 T1-T5 全 PASS（首次会调真实 AI ~¥0.5）
```

如果某个测试不达标：
- T1 不到 8 个 ##：调整 prompt 强调"只写本节，不要写其他"
- T2/T3 字数不够：subtopic prompt 加更狠"必须 ≥1000 字"
- T4 量化指标不够：prompt 加"至少 5 处数字+单位"提示
- T5 重复：prev_summary 增加每节摘要长度

### Step 4：部署 + 真实章节验证（15 分钟）

```bash
rsync 改动文件
ssh restart bid-system
浏览器进项目 15 → "整体服务方案"章节 → AI 生成
观察：
  - SSE 是否持续推送 progress + content 事件
  - 整章是否包含 10 个 ## 标题
  - 字数是否 ≥ 7000
```

### Step 5：原子 commit + merge → master（10 分钟）

```bash
git commit -m "feat(bid-ai): per-subtopic multi-turn section generation"
git checkout master
git merge --ff-only feature/multi-turn-generation
git push origin master
git branch -d feature/multi-turn-generation
```

---

## 二、文件清单

| 文件 | 改动 | 行数 |
|---|---|---|
| `backend/app/services/bid_ai_service.py` | 重构（新增 4 个方法）| +180 / -10 |
| `backend/scripts/test_multi_turn_generation.py` | 新增 | +200 |
| 前端 | 不动（向前兼容）| 0 |

---

## 三、风险与控制

| 风险 | 控制 |
|---|---|
| 单节耗时累加导致超时 | 每节 max_tokens=4096，单节 < 30s；总 ~3-5 分钟可接受 |
| 中间节失败导致整章 fail | try/except 单节包裹，失败节占位继续 |
| 用户不耐心等 5 分钟 | SSE progress 事件 + 实时 content 流，用户始终看到生成进度 |
| 成本意外升高 | max_tokens 限死 4096；监控调用次数 |
| 生成质量未达预期 | 测试 T1-T5 量化标准，未达则迭代 prompt |

---

## 四、不做（v2）

- 失败节自动重试一次
- 跨节 AI 去重检测（v1 靠 prev_summary）
- 用户可勾选某些子主题不写
- 按招标类型动态调整 checklist
