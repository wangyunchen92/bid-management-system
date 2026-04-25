# 招标文件模板抽取与一键填入设计

**日期**：2026-04-25
**模块**：标书编制 - 框架生成
**背景**：客户反馈现有「一键填入招标信息」只生成空章节标题，没有把招标文件中已提供的模板原文（响应函格式、报价表样式等）一起带入，仍需用户手动复制。

---

## 一、目标

解析招标文件后，"一键填入"应：
1. 用招标文件解析出的章节作为框架（而非沿用 25 章标准模板）
2. 自动从招标文件原文中抽取每个章节对应的模板原文，填入 `section.content`
3. 补齐招标文件未列出但政采必备的章节（中小企业声明函等）
4. 末尾追加"补充信息"章节供用户从企业资料库挑选附加资料

---

## 二、整体流程

```
[招标文件已解析] ──┐
                   │
   用户点「一键填入招标信息」
                   │
   ① AI 二次抽取模板原文（基于 raw_text + 章节名）
      │  约 30-60 秒，SSE 流式进度反馈
      │
   ② 章节合并
      │  解析章节
      │  + 必备但未识别的章节（fallback 列表）
      │  + "补充信息"章节（LIBRARY 类型）
      │
   ③ 批量创建 BidSection
      │  content = AI 抽取的模板原文（找不到留空）
      │  section_type = AI 推断
      │
   ④ 关闭 Drawer，章节树刷新，默认选中第 1 章
```

旧的「一键生成框架」按钮（用 25 章标准模板）保留为 fallback，仅当未解析过招标文件时显示。

---

## 三、AI 抽取模板（核心）

### 新增方法

`tender_ai_parser.extract_chapter_templates(raw_text: str, chapter_titles: List[str]) -> dict`

### Prompt 设计

```
你是招标文件分析助手。从招标文件中为以下投标章节抽取对应的模板原文。

投标章节列表：
1. 磋商响应函
2. 报价表
3. ...

招标文件原文：
[raw_text，截断到 150K 字符]

任务：
- 找到招标文件中"响应文件格式""投标文件格式""附件"等部分
- 为每个章节匹配对应的模板（如"响应函" 对应 "格式一：响应函"）
- 把模板原文原样摘出（保留表格、空白下划线、签章位等）
- 推断每章类型：
    TEMPLATE：固定格式文件（响应函、声明函、承诺函、授权委托书）
    MANUAL：需手动填写数据（报价表、价格表）
    AI_GENERATE：需撰写方案（技术方案、服务方案、商务/技术偏离表）
    LIBRARY：附资料（业绩证明、人员清单、资质证书）

严格按以下 JSON 输出（不要包裹 ```）：
{
  "chapters": [
    {
      "title": "磋商响应函",
      "section_type": "TEMPLATE",
      "template": "...原文模板，找不到时填空字符串...",
      "matched": true | false
    }
  ]
}
```

### Token 预算
- input: ≤150K 字符
- output: ≤8K tokens（10 章 × 平均 1K 字 = 充裕）
- 单次调用，模型 `doubao-seed-1.8`，temperature=0.1

### 失败降级
AI 调用失败/JSON 解析失败时：
- 仍创建章节框架（标题 + 推断类型）
- content 全留空
- 给用户提示"AI 模板抽取失败，已创建空章节"

---

## 四、章节合并逻辑

### 必备 fallback 章节
```python
ESSENTIAL_FALLBACK = [
    "无重大违法记录声明函",
    "中小企业声明函",
    "法定代表人身份证明书",
    "授权委托书",
]
```

### 合并规则
1. 取 AI 抽取返回的章节列表（含 type + template）作为基础
2. 遍历 `ESSENTIAL_FALLBACK`：若标准框架中的该章节未被解析章节"匹配命中"（用 `STANDARD_FRAMEWORK[i].keywords` 判定），则补充进来（type 沿用 `STANDARD_FRAMEWORK`，content 留空）
3. 末尾追加 `{"title": "补充信息", "section_type": "LIBRARY", "content": ""}`

### 排序
按合并后顺序写入 `sort_order = 1, 2, 3, ...`

---

## 五、API 设计

### 新增端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/bid/projects/{project_id}/framework-from-tender` | 基于招标文件抽取模板并生成章节框架 |

### 请求体
```json
{
  "tender_doc_id": 123
}
```

### 响应（SSE 流式）

```
event: extract_start
data: {"chapter_count": 7}

event: extract_done
data: {"matched_count": 5, "duration_ms": 42000}

event: section_created
data: {"title": "磋商响应函", "section_type": "TEMPLATE", "has_content": true}

event: done
data: {"total": 10, "with_content": 6}

event: error
data: {"message": "..."}
```

### 错误处理
- `tender_doc_id` 不存在或不属于当前 project_id 的关联 tender → 400
- `raw_text` 为空 → 400 "招标文件未解析完成"
- 项目已存在章节 → 400 "项目已有章节，请先清空"（或后续考虑覆盖选项）

---

## 六、后端代码改造

### `tender_ai_parser.py`
- 新增 `extract_chapter_templates(raw_text, chapter_titles)` 方法
- 复用 `_get_client()`，调用 `settings.AI_MODEL`
- JSON 容错处理（同 `parse()` 方法）

### `bid_framework_service.py`
- 新增 `async def generate_from_tender(db, project_id, tender_doc_id, user_id) -> AsyncIterator[dict]`
  - 异步生成器，yield 各阶段事件供 SSE 推送
  - 内部步骤：拿招标文件 → 调 AI 抽取 → 合并章节 → 创建 sections
- 复用现有 `_match_template()`、`_fill_template()`：仅当某章 `section_type == "TEMPLATE"` 且 AI 未抽取到模板内容（matched=false）时，回退到知识库模板填充逻辑
- `_merge_with_standard()` 适当调整以适应新数据结构

### `routers/bid.py`
- 新增 `POST /projects/{project_id}/framework-from-tender` SSE 端点
- 参考 `runBidDetection` 的 SSE 实现模式

### 数据库
- 无 schema 变更，复用 `BidSection` 现有字段（title, content, section_type, sort_order, status）

---

## 七、前端改造

### `frontend/src/components/TenderDocParser/index.tsx`
- 顶部"解析到 N 个章节建议"卡片中的「一键填入招标信息」按钮：
  - 旧行为：触发父组件 `onParseComplete(result)` → 父组件弹 Modal.confirm 循环 createSection
  - 新行为：直接调用 `generateFrameworkFromTender(projectId, tenderDocId, ...)`，按 SSE 事件更新进度
- 按钮 loading 时展开进度面板：
  ```
  [✓] AI 抽取模板原文中... (35s)
  [✓] 已生成 10 个章节，其中 6 个含模板内容
  ```
- 完成后调用 `onParseComplete()` 通知父组件刷新

### `frontend/src/pages/Bid/Workbench/index.tsx`
- 移除 `<TenderDocParser onParseComplete={...}>` 中的 `Modal.confirm` + 循环 createSection 逻辑
- `onParseComplete` 改为：`loadSections()` + 关闭 Drawer + 选中第 1 章
- 「一键生成框架」按钮（左侧栏空状态）保留为 fallback：
  - 显示条件：`sections.length === 0 && !hasTenderDoc`
  - 解析过招标文件的项目隐藏此按钮，引导用户走「招标文件解析」入口

### `frontend/src/services/bid.ts`
新增 SSE 方法（参考已有 `runBidDetection`）：
```ts
generateFrameworkFromTender(
  projectId: number,
  tenderDocId: number,
  onExtractStart: (count: number) => void,
  onExtractDone: (matched: number, duration: number) => void,
  onSectionCreated: (title: string, type: string, hasContent: boolean) => void,
  onDone: (total: number, withContent: number) => void,
  onError: (msg: string) => void,
): Promise<void>
```

---

## 八、用户体验细节

| 场景 | 提示 |
|---|---|
| 抽取中 | Drawer 内进度条，显示已耗时 |
| 全部成功 | Toast: `已生成 10 个章节，其中 6 个含招标文件模板原文，可直接编辑` |
| 部分匹配 | Toast: `已生成 10 个章节（4 个章节未在招标文件中找到模板，需手动撰写）` |
| AI 完全失败 | Toast 警告: `AI 模板抽取失败，已创建空章节框架，请手动填写` |
| 项目已有章节 | 弹窗提示需先清空，或暂不允许覆盖（首版禁用） |

---

## 九、测试要点

1. **接口测试**
   - 用真实招标文件（学院学生档案印刷服务）走完整流程
   - 验证 SSE 事件序列正确
   - 验证生成的 BidSection 数量、type 分布、content 非空率
2. **降级测试**
   - mock AI 调用抛异常 → 仍能创建空章节框架
   - mock AI 返回非法 JSON → 同上
3. **页面实操（Playwright）**
   - 上传招标文件 → 解析 → 点「一键填入」
   - 验证章节树自动刷新、第 1 章自动选中、模板原文已显示
   - 验证「一键生成框架」按钮仅在未解析时出现
4. **回归**
   - 旧项目（无 tender_doc）走「一键生成框架」流程仍正常
   - 「批量 AI 生成」「填充资料库」等下游功能仍工作

---

## 十、范围外（不在本次改动）

- "补充信息"章节的 UI 选择交互（沿用现有「填充资料库」按钮）
- 章节抽取失败时的重试机制
- 用户在弹窗里勾选/排序章节后再生成（已在讨论中排除）
- 单独抽取某一章节模板（按需后续再加）
