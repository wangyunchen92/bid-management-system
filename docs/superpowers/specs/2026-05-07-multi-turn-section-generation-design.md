# 设计文档 — 方案 A：分子主题多轮生成

**日期**：2026-05-07
**分支**：`feature/multi-turn-generation`
**回退点**：master `2ac2af15`（RAG 已合并）
**关联**：RAG 是数据层提升，本设计是结构层提升，两者叠加

---

## 一、问题与目标

### 1.1 当前 (RAG 后) 状态

`bid_ai_service.generate_section_content_stream` 一次大调用产出整章。SECTION_CHECKLIST 给"服务方案"配了 10 个子主题，但实际 AI 输出还是只展开 5-6 个 ##，每节 200-400 字，整章 ~1500-2000 字（真人 10000+）。

**根因**：单次大 prompt 让 AI 注意力在 10 个子主题间分散，每个都"够用就好"。max_tokens=8192 也没用满。

### 1.2 目标

把"一次大 prompt 写整章"换成"**每个 ## 子主题独立调一次 AI**"：

```
当前：    1 次 AI 调用 → 10 个 ## → 每个 ~250 字 → 总 ~2000 字
改造后：  10 次 AI 调用 → 每次只写 1 个 ## → 每个 ~1000 字 → 总 ~10000 字
```

每次独立调用：
- AI 注意力 100% 给一个子主题 → 深度展开
- prompt 里的 RAG 检索按**该子主题的具体描述**查询，命中更精准
- 已生成的前面 ## 摘要作上下文，保证整章连贯
- SSE 流式：用户看到 10 节逐步累加（30s → 3-5 分钟，但 UX 是"逐步成形"而非"长时等待"）

---

## 二、技术方案

### 2.1 关键决策

| 议题 | 决策 |
|---|---|
| 触发条件 | 章节有 SECTION_CHECKLIST 时走多轮；无 checklist 时退回单轮 |
| RAG 查询粒度 | **子主题级**：query = `f"{章节标题} - {子主题名} {hint}"`（不再用纯章节名）|
| 每节字数目标 | 单节 prompt 要求 800-1500 字 |
| 每节 max_tokens | 4096（单节够用，无需 8192）|
| temperature | 0.4（已定）|
| 节间衔接 | 每次生成时，把前面已写完的章节标题列表 + 各 ## 末段 100 字作为"已写章节回顾"注入 |
| SSE 事件类型 | 现有 `{content: ...}` 不变，每节流式推送；新增 `{progress: {section_idx, section_total, section_title}}` 让前端显示进度 |
| 失败容错 | 单节失败 → 记录错误并继续下一节，最终拼接时跳过失败节（不让一节崩了整章 fail）|

### 2.2 流程图

```
multi_turn_generate(section, db)
  │
  ├─ checklist = self._section_title_to_checklist(section.title)
  ├─ if not checklist: return single_turn_generate(section)  # fallback
  │
  ├─ 收集共享上下文（一次性，复用 N 次）
  │   ├─ company_info     ← 22 业绩 + 资质 等
  │   ├─ tender_req       ← 招标文件解析结果
  │   └─ scoring_block    ← 关联评分项
  │
  ├─ 累加生成
  │   for idx, item in enumerate(checklist):
  │       ├─ subtopic_title = "一、xxx"  (从 item 切出来)
  │       ├─ subtopic_hint  = "（xxx）"  (从 item 切出来)
  │       ├─ rag_ref = self._get_knowledge_reference(
  │       │              query = f"{section.title} - {subtopic_title} {hint}"
  │       │            )                                       ← 子主题级 RAG
  │       │
  │       ├─ prev_summary = "已写章节回顾：\n" + 已生成 ## 标题 + 末段 100 字
  │       │
  │       ├─ subtopic_prompt = build_subtopic_prompt(
  │       │      section_title, subtopic_title, subtopic_hint,
  │       │      rag_ref, company_info, scoring_block, prev_summary
  │       │   )
  │       │
  │       ├─ yield {progress: {idx+1, total, subtopic_title}}  ← 推前端进度
  │       │
  │       ├─ stream chat completion (max_tokens=4096)
  │       │     for chunk in stream:
  │       │         yield {content: chunk}                      ← 实时推
  │       │         buffer += chunk
  │       │
  │       └─ all_sections.append(buffer)  # 已生成的累加
  │
  └─ 完成（前端拼好所有 chunk 就是完整章节）
```

### 2.3 子主题 prompt 模板

```
你是标书撰写专家，正在分子主题深度展开「{section_title}」章节。
当前要写的子主题是【{subtopic_title}】，前面已经写过的子主题如下，请确保新内容与之衔接、不重复：

{prev_summary}

{rag_ref}              ← RAG 检索的本子主题最相关的真投标段落（5-8 段）

{tender_req}           ← 招标要求（精简版）

{company_info}         ← 企业资料库（业绩/资质/人员/设备）

{scoring_block}        ← 关联评分项（如有）

【本节硬性要求】
1. 严格写当前子主题：{subtopic_title}
   {subtopic_hint}
2. 篇幅 800-1500 字（这是单节，不是整章）
3. 三级 markdown：## {subtopic_title} → ### x.1/x.2/x.3 → （1）（2）（3）
4. 至少 5 处量化指标（数字+单位），不允许"较高""丰富"等空话
5. 必用印刷行业术语，引用真投标参考的细节密度
6. 引用企业素材时具体到「项目名（甲方+金额+年份）」
7. 直接以 ## 开头输出，不要"以下是..."引导语，不要写其他子主题
```

### 2.4 共享上下文 vs 每节独立部分

| 内容 | 共享（一次性建）| 每节独立 |
|---|---|---|
| 企业资料库 (company_info) | ✅ |  |
| 招标要求 (tender_req) | ✅ |  |
| 评分项关联 (scoring_block) | ✅ |  |
| RAG 参考样本 |  | ✅ 每节独立查询 |
| 前面已写章节摘要 |  | ✅ 累加 |
| 子主题 prompt（标题/hint/要求）|  | ✅ |

### 2.5 SSE 协议改动

**现有事件**：
- `{"content": "...生成的文字..."}`
- `{"done": true}` 或 `{"error": "..."}`

**新增事件**：
- `{"progress": {"current": 3, "total": 10, "subtopic": "三、质量管控体系"}}` ← 多轮专用
- `{"section_done": {"subtopic": "二、工艺执行能力", "word_count": 1234}}` ← 一节完成

**前端改动**：可不改（多余事件忽略），也可加进度条显示。本设计以**前端不改**为前提（最小入侵）。

---

## 三、影响范围

| 文件 | 改动 |
|---|---|
| `backend/app/services/bid_ai_service.py` | 新增 `_multi_turn_section_stream()` 主逻辑；`generate_section_content_stream()` 入口判断 checklist 后路由 |
| `backend/app/services/bid_ai_service.py` | 新增子主题 prompt builder + prev_summary 拼接 helper |
| `backend/app/routers/bid.py` | SSE 事件解析处理多余字段（`progress` / `section_done`），但向前兼容旧 `content` 流 |
| `backend/scripts/test_multi_turn_generation.py` | 新增端到端测试脚本（验收 T1-T5）|
| 前端 `aiGenerateSectionStream` | **可不改**；如想加进度条另说 |

---

## 四、成本

| 项目 | 当前（单轮）| 多轮 |
|---|---|---|
| AI chat 调用次数（10 项 checklist 章节）| 1 | **10** |
| AI 输入 tokens | ~6K | ~6K × 10 = ~60K |
| AI 输出 tokens | ~3K | ~5K × 10 = ~50K |
| RAG embedding 查询次数 | 1 | **10** |
| 单章节单价（doubao seed-1.8）| ~¥0.05 | **~¥0.5** |
| 一份完整标书（~10 个 AI_GENERATE 章节）| ~¥0.5 | **~¥5** |
| 章节生成总耗时 | ~30s | **~3-5 分钟**（流式可见进度）|

**结论**：成本 10 倍但**预期生成质量翻 5 倍以上**，单章节字数从 2000 → 10000+。一份标书 ¥5 是可接受的。

---

## 五、验收标准（T1-T5）

| # | 用例 | 期望 |
|---|---|---|
| T1 | "服务方案"章节多轮生成 | 输出含 ≥ 8 个 `## 一/二/三/...` 标题（10 项 checklist 至少完成 8 项）|
| T2 | 单节字数 | 平均 ≥ 800 字（不足 500 字的节占比 < 30%）|
| T3 | 整章字数 | ≥ 7000 字（接近真投标）|
| T4 | 量化指标密度 | 整章 ≥ 50 处带数字+单位的指标 |
| T5 | 章节连贯性 | 各 ## 之间不重复（同一段话不在两个 ## 出现）|

---

## 六、风险与缓解

| 风险 | 缓解 |
|---|---|
| 中间某节 AI 调用失败 | try/except 捕获，记录失败节，最后输出"该节生成失败，请重试此节"占位，整章不 fail |
| 总耗时 3-5 分钟用户没耐心 | SSE 流式让用户实时看到生成，每节推 progress 事件提示进度 |
| 节间内容重复 | prev_summary 注入已写章节末段，prompt 强调"不要重复" |
| 成本意外升高 | 监控 + 章节级 max_tokens=4096 限死，单节最多 ~3000 字输出 |
| 前端 UX 中断 | 现有 SSE 已支持流式，多余事件类型客户端会自动忽略 |

---

## 七、不在本设计内（v2）

- 失败节自动重试 1 次（v1 直接占位）
- 跨节去重的 AI 检测（v1 靠 prompt + prev_summary）
- 用户可手动跳过某些子主题（v1 全 checklist 必写）
- 与 SECTION_CHECKLIST 联动的"按招标类型选不同 checklist"（v3）

---

## 八、回退方案

- 单步回退：`generate_section_content_stream` 入口判断改回直接走 `_single_turn_section_stream()`，热重载即可
- 整体回退：`git checkout master`，pkl 不变，无数据后果
