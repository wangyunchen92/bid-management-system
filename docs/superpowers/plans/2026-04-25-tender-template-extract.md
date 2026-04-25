# 招标文件模板抽取与一键填入 - 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改造「一键填入招标信息」按钮：解析招标文件后，AI 二次抽取每个章节的模板原文并填入 `section.content`，让用户拿到带模板的章节框架而不是空标题。

**Architecture:** 后端新增 `tender_ai_parser.extract_chapter_templates()` AI 抽取方法 + `bid_framework_service.generate_from_tender()` 异步生成器（SSE），路由层新增 SSE 端点。前端 `TenderDocParser` 按钮改调新 SSE API 并显示进度，`Workbench` 移除旧的循环 createSection 逻辑、把「一键生成框架」改成 fallback。

**Tech Stack:** Python FastAPI + SQLAlchemy 异步 / React + TypeScript + Ant Design / 火山引擎豆包 doubao-seed-1.8 / SSE 流式

**Spec:** `docs/superpowers/specs/2026-04-25-tender-template-extract-design.md`

---

## 文件清单

### 后端（修改）
- `backend/app/services/tender_ai_parser.py` — 新增 `extract_chapter_templates(raw_text, chapter_titles)` 方法（约 60 行）
- `backend/app/services/bid_framework_service.py` — 新增 `generate_from_tender(...)` 异步生成器方法（约 80 行）
- `backend/app/routers/bid.py` — 新增 `POST /projects/{project_id}/framework-from-tender` SSE 端点（约 30 行）

### 前端（修改）
- `frontend/src/constants/api.ts` — 新增 `PROJECT_FRAMEWORK_FROM_TENDER` 路由常量
- `frontend/src/services/bid.ts` — 新增 `generateFrameworkFromTender()` SSE 方法（约 50 行）
- `frontend/src/components/TenderDocParser/index.tsx` — 改造「一键填入招标信息」按钮，新增进度面板
- `frontend/src/pages/Bid/Workbench/index.tsx` — 移除 Modal.confirm + 循环 createSection，调整「一键生成框架」按钮显示条件

### 文档
- `RELEASE_NOTES.md` 或 `CLAUDE.md` 近期更新区追加一行变更说明

---

## Task 1: 后端 — AI 抽取模板方法

**Files:**
- Modify: `backend/app/services/tender_ai_parser.py`（在 `parse()` 方法之后追加）

- [ ] **Step 1: 新增 prompt 常量与方法**

打开 `backend/app/services/tender_ai_parser.py`，在文件顶部 `TENDER_PARSE_PROMPT` 之后追加：

```python
CHAPTER_TEMPLATE_EXTRACT_PROMPT = """你是招标文件分析助手。从招标文件中为以下投标章节抽取对应的模板原文。

任务：
1. 找到招标文件中"响应文件格式""投标文件格式""附件""格式一/二/三..."等部分
2. 为每个章节匹配对应的模板（如"磋商响应函"对应"格式一：响应函"）
3. 把模板原文**原样**摘出（保留表格、空白下划线 ___、签章位 (签章) 等）
4. 推断每章类型：
   - TEMPLATE：固定格式文件（响应函、声明函、承诺函、授权委托书、身份证明）
   - MANUAL：需手动填写数据（报价表、价格表、分项报价）
   - AI_GENERATE：需撰写方案（技术方案、服务方案、商务/技术偏离表）
   - LIBRARY：附资料（业绩证明、人员清单、资质证书、设备清单）

严格按以下 JSON 输出（不要包裹 ```）：
{
  "chapters": [
    {
      "title": "磋商响应函",
      "section_type": "TEMPLATE",
      "template": "...原文模板，找不到时填空字符串...",
      "matched": true
    }
  ]
}
"""
```

然后在 `TenderAIParser` 类内部、`parse()` 方法之后追加新方法：

```python
    def extract_chapter_templates(self, raw_text: str, chapter_titles: list) -> dict:
        """从招标文件原文中为指定章节抽取模板原文。
        返回 {"chapters": [{"title", "section_type", "template", "matched"}]}
        """
        if not chapter_titles:
            return {"chapters": []}

        client = self._get_client()

        # 截断过长文本（预留输出空间）
        max_chars = 150000
        if len(raw_text) > max_chars:
            raw_text = raw_text[:max_chars] + "\n\n[文档过长，已截断]"

        chapter_list_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(chapter_titles))
        user_prompt = f"投标章节列表：\n{chapter_list_text}\n\n招标文件原文：\n{raw_text}"

        try:
            response = client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": CHAPTER_TEMPLATE_EXTRACT_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=8192,
                temperature=0.1,
            )
            result_text = response.choices[0].message.content.strip()

            # 清理 markdown 包裹
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text
                if result_text.endswith("```"):
                    result_text = result_text[:-3]

            data = json.loads(result_text)
            if not isinstance(data, dict) or "chapters" not in data:
                raise ValueError("AI 返回缺少 chapters 字段")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"AI 模板抽取 JSON 解析失败: {e}")
            raise Exception(f"AI 返回格式异常: {e}")
        except Exception as e:
            logger.error(f"AI 模板抽取失败: {e}")
            raise
```

- [ ] **Step 2: 手动验证语法**

```bash
cd backend && python3 -c "from app.services.tender_ai_parser import tender_ai_parser; print('OK', hasattr(tender_ai_parser, 'extract_chapter_templates'))"
```
Expected: `OK True`

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/tender_ai_parser.py
git commit -m "feat(bid): add AI method to extract chapter templates from tender doc"
```

---

## Task 2: 后端 — 框架生成服务（异步生成器）

**Files:**
- Modify: `backend/app/services/bid_framework_service.py`（在类内部追加方法）

- [ ] **Step 1: 在类顶部添加常量**

在 `STANDARD_FRAMEWORK = [...]` 列表之后、`class BidFrameworkService` 之前追加：

```python
# 招标文件未列出但政采必备的章节（fallback 补充）
ESSENTIAL_FALLBACK_TITLES = [
    "无重大违法记录声明函",
    "中小企业声明函",
    "法定代表人身份证明书",
    "授权委托书",
]

# "补充信息"章节（追加到末尾）
SUPPLEMENT_CHAPTER = {
    "title": "补充信息",
    "section_type": "LIBRARY",
    "template": "",
    "keywords": ["资料", "附件", "补充"],
    "description": "补充资料：可从企业资料库选择需附上的资质证书、业绩案例、人员证书等",
}
```

- [ ] **Step 2: 添加 import**

文件顶部 `from typing import List, Optional` 改为：
```python
from typing import AsyncIterator, List, Optional
```

- [ ] **Step 3: 添加 `generate_from_tender()` 方法**

在 `BidFrameworkService` 类内部、`generate_framework()` 方法之后追加：

```python
    async def generate_from_tender(
        self,
        db: AsyncSession,
        project_id: int,
        tender_doc_id: int,
        user_id: int,
    ) -> AsyncIterator[dict]:
        """基于招标文件解析结果生成章节框架。异步生成器，yield SSE 事件。

        事件类型：
          - extract_start: {chapter_count}
          - extract_done: {matched_count, duration_ms}
          - extract_failed: {message}（降级，仍继续创建空章节）
          - section_created: {title, section_type, has_content}
          - done: {total, with_content}
          - error: {message}
        """
        import json as _json
        import time
        from app.models.tender_document import TenderDocument
        from app.services.tender_ai_parser import tender_ai_parser

        # 1. 校验项目存在
        proj_result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            yield {"type": "error", "message": "标书项目不存在"}
            return

        # 2. 校验项目是否已有章节
        from app.models.bid import BidSection as _BS
        existing = await db.execute(
            select(_BS).where(_BS.project_id == project_id, _BS.is_deleted == 0).limit(1)
        )
        if existing.scalar_one_or_none():
            yield {"type": "error", "message": "项目已有章节，请先清空再生成"}
            return

        # 3. 拿招标文件
        td_result = await db.execute(
            select(TenderDocument).where(TenderDocument.id == tender_doc_id, TenderDocument.is_deleted == 0)
        )
        td = td_result.scalar_one_or_none()
        if not td:
            yield {"type": "error", "message": "招标文件不存在"}
            return
        if not td.raw_text:
            yield {"type": "error", "message": "招标文件未解析完成（缺少 raw_text）"}
            return
        if not td.parse_result:
            yield {"type": "error", "message": "招标文件未解析完成（缺少解析结果）"}
            return

        try:
            parse_result = _json.loads(td.parse_result) if isinstance(td.parse_result, str) else td.parse_result
        except Exception:
            yield {"type": "error", "message": "招标文件解析结果格式异常"}
            return

        chapter_titles = (parse_result.get("bid_document_requirements") or {}).get("chapters") or []
        if not chapter_titles:
            yield {"type": "error", "message": "招标文件未识别到章节列表"}
            return

        # 4. AI 抽取模板（带降级）
        yield {"type": "extract_start", "chapter_count": len(chapter_titles)}

        ai_chapters = []
        t0 = time.time()
        try:
            extract_result = tender_ai_parser.extract_chapter_templates(td.raw_text, chapter_titles)
            ai_chapters = extract_result.get("chapters", [])
            matched_count = sum(1 for c in ai_chapters if c.get("matched"))
            duration_ms = int((time.time() - t0) * 1000)
            yield {"type": "extract_done", "matched_count": matched_count, "duration_ms": duration_ms}
        except Exception as e:
            duration_ms = int((time.time() - t0) * 1000)
            logger.warning(f"AI 模板抽取失败，降级为空章节: {e}")
            yield {"type": "extract_failed", "message": str(e), "duration_ms": duration_ms}
            # 降级：用解析章节构造空模板
            ai_chapters = [
                {
                    "title": t,
                    "section_type": self._infer_type(t),
                    "template": "",
                    "matched": False,
                }
                for t in chapter_titles
            ]

        # 5. 合并章节（解析章节 + ESSENTIAL_FALLBACK 补充 + 补充信息章节）
        merged = self._merge_chapters_for_tender(ai_chapters)

        # 6. 批量创建 BidSection
        with_content = 0
        for i, chapter in enumerate(merged):
            content = chapter.get("template") or ""
            section_type = chapter.get("section_type") or self._infer_type(chapter["title"])

            # TEMPLATE 类型且 AI 没抽到模板，回退用知识库模板
            if section_type == "TEMPLATE" and not content:
                template_id = await self._match_template(db, [chapter["title"]])
                if template_id:
                    content = await self._fill_template(db, template_id, project)

            section = BidSection(
                project_id=project_id,
                title=chapter["title"],
                content=content,
                sort_order=i + 1,
                section_type=section_type,
                status="COMPLETED" if content else "PENDING",
                word_count=len(content) if content else 0,
                created_by=user_id,
                updated_by=user_id,
            )
            db.add(section)
            await db.flush()

            if content:
                with_content += 1

            yield {
                "type": "section_created",
                "title": chapter["title"],
                "section_type": section_type,
                "has_content": bool(content),
            }

        await db.commit()
        yield {"type": "done", "total": len(merged), "with_content": with_content}

    def _merge_chapters_for_tender(self, ai_chapters: list) -> list:
        """合并 AI 抽取的章节 + ESSENTIAL_FALLBACK 必备补充 + 补充信息章节。
        返回最终章节列表 [{title, section_type, template, matched}]。
        """
        result = list(ai_chapters)
        existing_titles_text = " ".join(c.get("title", "") for c in ai_chapters)

        for std in STANDARD_FRAMEWORK:
            if std["title"] not in ESSENTIAL_FALLBACK_TITLES:
                continue
            # 用关键词判定是否已经有类似章节
            has_similar = any(kw in existing_titles_text for kw in std.get("keywords", []))
            if not has_similar:
                result.append({
                    "title": std["title"],
                    "section_type": std["section_type"],
                    "template": "",
                    "matched": False,
                })

        result.append({
            "title": SUPPLEMENT_CHAPTER["title"],
            "section_type": SUPPLEMENT_CHAPTER["section_type"],
            "template": SUPPLEMENT_CHAPTER["template"],
            "matched": False,
        })
        return result
```

- [ ] **Step 4: 手动验证语法**

```bash
cd backend && python3 -c "from app.services.bid_framework_service import bid_framework_service; print('OK', hasattr(bid_framework_service, 'generate_from_tender'), hasattr(bid_framework_service, '_merge_chapters_for_tender'))"
```
Expected: `OK True True`

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/bid_framework_service.py
git commit -m "feat(bid): add generate_from_tender service with AI template extraction"
```

---

## Task 3: 后端 — SSE 路由端点

**Files:**
- Modify: `backend/app/routers/bid.py`（在「框架生成」区块追加）
- Modify: `backend/app/schemas/bid.py`（追加请求 schema）

- [ ] **Step 1: 添加请求 schema**

打开 `backend/app/schemas/bid.py`，在文件末尾追加：

```python
class FrameworkFromTenderRequest(BaseModel):
    tender_doc_id: int
```

如果文件顶部还没有 `from pydantic import BaseModel` 等 import，复用现有的即可。

- [ ] **Step 2: 添加 SSE 路由**

打开 `backend/app/routers/bid.py`，在 `# ========== 框架生成 ==========` 区块下、`generate_framework` 函数之后追加：

```python
@router.post("/projects/{project_id}/framework-from-tender", summary="基于招标文件抽取模板生成框架（SSE流式）")
async def generate_framework_from_tender(
    project_id: int,
    data: "FrameworkFromTenderRequest",
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """基于招标文件解析结果，AI 抽取每章模板原文并生成章节框架。SSE 流式推送进度。"""
    from app.services.bid_framework_service import bid_framework_service

    async def event_generator():
        try:
            async for event in bid_framework_service.generate_from_tender(
                db, project_id, data.tender_doc_id, user_id
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

并在文件顶部 import 区块追加：
```python
from app.schemas.bid import (
    BidProjectCreate, BidProjectUpdate,
    BidSectionCreate, BidSectionUpdate,
    ReorderSectionsRequest,
    AIGenerateRequest, AIGenerateResponse,
    BidCheckRequest,
    FrameworkFromTenderRequest,   # ← 追加
)
```

并把上面函数签名里 `data: "FrameworkFromTenderRequest"` 的引号去掉：
```python
data: FrameworkFromTenderRequest,
```

- [ ] **Step 3: 启动后端验证语法**

```bash
cd backend && python3 -c "from app.main import app; print('OK', any('framework-from-tender' in r.path for r in app.routes))"
```
Expected: `OK True`

- [ ] **Step 4: 提交**

```bash
git add backend/app/routers/bid.py backend/app/schemas/bid.py
git commit -m "feat(bid): add SSE endpoint /framework-from-tender"
```

---

## Task 4: 后端接口手动验证（curl）

**Files:** 仅查询，不修改

- [ ] **Step 1: 启动后端服务**

```bash
cd backend && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```
Expected: 服务启动成功，无报错

- [ ] **Step 2: 登录拿 token**

```bash
curl -s -X POST http://127.0.0.1:8002/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -m json.tool
```
Expected: 返回 `data.access_token`

- [ ] **Step 3: 查找一个已解析过招标文件的项目**

```bash
TOKEN="<上一步的 access_token>"
# 列出所有招标文件，找一个 parse_status=COMPLETED 且 raw_text 非空的
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8002/api/v1/bid/projects?page=1&page_size=20" | python3 -m json.tool
# 找到一个 project_id，然后查它关联的 tender_doc：
PROJECT_ID=<从上面找一个>
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8002/api/v1/tender-doc/by-project/$PROJECT_ID" | python3 -m json.tool
```
Expected: 拿到 `tender_doc_id` 和 `parse_status: "COMPLETED"`

- [ ] **Step 4: 准备一个新空项目（必要时）**

如果第 3 步找到的项目已经有章节，需要新建一个空项目并关联同一个 tender_doc：
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"测试-模板抽取","tender_id":<tender_id>}' \
  http://127.0.0.1:8002/api/v1/bid/projects | python3 -m json.tool
```
（或直接清空已有项目的章节）

- [ ] **Step 5: 调 SSE 接口**

```bash
TENDER_DOC_ID=<上面拿到的>
curl -N -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"tender_doc_id\":$TENDER_DOC_ID}" \
  http://127.0.0.1:8002/api/v1/bid/projects/$PROJECT_ID/framework-from-tender
```
Expected: SSE 流式输出，依次看到：
```
data: {"type": "extract_start", "chapter_count": N}
data: {"type": "extract_done", "matched_count": M, "duration_ms": ...}
data: {"type": "section_created", "title": "...", "section_type": "...", "has_content": true|false}
... (每章一条)
data: {"type": "done", "total": ..., "with_content": ...}
```

- [ ] **Step 6: 验证章节落库**

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8002/api/v1/bid/projects/$PROJECT_ID/sections" | python3 -m json.tool | head -80
```
Expected:
- 返回的章节数 = 解析章节数 + 必备补充数 + 1（补充信息）
- 至少几个章节 `content` 非空且 `status: "COMPLETED"`
- 末尾章节 `title: "补充信息"` 且 `section_type: "LIBRARY"`

- [ ] **Step 7: 验证错误路径 — 重复生成**

再次对同一个已生成的项目调一次：
```bash
curl -N -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"tender_doc_id\":$TENDER_DOC_ID}" \
  http://127.0.0.1:8002/api/v1/bid/projects/$PROJECT_ID/framework-from-tender
```
Expected: 收到 `data: {"type": "error", "message": "项目已有章节，请先清空再生成"}`

- [ ] **Step 8: 提交（如需要修复 bug）**

如果上述任意步骤失败，回到 Task 1/2/3 修复，并新建 commit：
```bash
git commit -m "fix(bid): <具体修复点>"
```
否则跳过此步。

---

## Task 5: 前端 — API 常量与 service 方法

**Files:**
- Modify: `frontend/src/constants/api.ts`
- Modify: `frontend/src/services/bid.ts`

- [ ] **Step 1: 添加 API 常量**

打开 `frontend/src/constants/api.ts`，在 `BID_API` 对象内 `PROJECT_BATCH_AI` 之后追加：

```typescript
  PROJECT_FRAMEWORK_FROM_TENDER: (projectId: number) => `${API_PREFIX}/bid/projects/${projectId}/framework-from-tender`,
```

- [ ] **Step 2: 添加 service 方法**

打开 `frontend/src/services/bid.ts`，在 `generateBidFramework` 函数之后追加：

```typescript
export async function generateFrameworkFromTender(
  projectId: number,
  tenderDocId: number,
  onExtractStart: (chapterCount: number) => void,
  onExtractDone: (matchedCount: number, durationMs: number) => void,
  onExtractFailed: (message: string, durationMs: number) => void,
  onSectionCreated: (title: string, sectionType: string, hasContent: boolean) => void,
  onDone: (total: number, withContent: number) => void,
  onError: (message: string) => void,
) {
  const token = localStorage.getItem('bid_system_access_token');
  const response = await fetch(BID_API.PROJECT_FRAMEWORK_FROM_TENDER(projectId), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ tender_doc_id: tenderDocId }),
  });

  if (!response.ok) {
    onError(`请求失败: ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) { onError('无法读取响应流'); return; }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const data = JSON.parse(line.slice(6));
        switch (data.type) {
          case 'extract_start': onExtractStart(data.chapter_count); break;
          case 'extract_done': onExtractDone(data.matched_count, data.duration_ms); break;
          case 'extract_failed': onExtractFailed(data.message, data.duration_ms); break;
          case 'section_created': onSectionCreated(data.title, data.section_type, data.has_content); break;
          case 'done': onDone(data.total, data.with_content); break;
          case 'error': onError(data.message); break;
        }
      } catch { /* skip */ }
    }
  }
}
```

- [ ] **Step 3: 类型检查**

```bash
cd frontend && npx tsc --noEmit
```
Expected: 无新增错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/constants/api.ts frontend/src/services/bid.ts
git commit -m "feat(bid): add frontend service for framework-from-tender SSE"
```

---

## Task 6: 前端 — 改造 TenderDocParser 组件

**Files:**
- Modify: `frontend/src/components/TenderDocParser/index.tsx`

- [ ] **Step 1: 修改 props 接口**

把 `TenderDocParserProps` 改为：

```typescript
interface TenderDocParserProps {
  projectId?: number;
  tenderId?: number;
  /** 章节框架生成完成后回调（生成的章节数和带模板的数量） */
  onFrameworkGenerated?: (totalSections: number, withContent: number) => void;
  /** 兼容：解析完成后回调（用于父组件保存解析结果等其他逻辑） */
  onParseComplete?: (result: TenderParseResult) => void;
}
```

并修改函数签名：
```typescript
export default function TenderDocParser({ projectId, tenderId, onFrameworkGenerated, onParseComplete }: TenderDocParserProps) {
```

- [ ] **Step 2: 添加 import**

文件顶部 import 区块追加：
```typescript
import { generateFrameworkFromTender } from '@/services/bid';
import { ThunderboltOutlined } from '@ant-design/icons';
```

并替换原有的 `import { Progress } from 'antd';` 行，把 `Progress` 合并到上面的 antd 导入：
```typescript
import {
  Upload, Spin, Tabs, Descriptions, Timeline, List, Table, Alert,
  Button, Typography, Tag, Space, App, Progress } from 'antd';
```
然后删除单独的 `import { Progress } from 'antd';` 行。

- [ ] **Step 3: 添加生成进度状态**

在组件内部状态区追加：
```typescript
  const [generating, setGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState<{
    phase: 'extract' | 'create' | 'done';
    message: string;
    sectionsCreated: number;
  } | null>(null);
```

- [ ] **Step 4: 替换"一键填入招标信息"按钮逻辑**

定位到当前的 `result.bid_document_requirements?.chapters && ... > 0 && (...)` 区块（约第 522-556 行），把里面的 `<Button onClick={...}>` 替换为：

```typescript
              <Button
                type="primary"
                size="small"
                loading={generating}
                disabled={!projectId || !docInfo?.id}
                style={{ background: 'linear-gradient(135deg, #0d9488, #14b8a6)', border: 'none', flexShrink: 0 }}
                icon={<ThunderboltOutlined />}
                onClick={async () => {
                  if (!projectId || !docInfo?.id) {
                    message.warning('缺少项目或招标文件信息');
                    return;
                  }
                  setGenerating(true);
                  setGenProgress({ phase: 'extract', message: '准备 AI 抽取章节模板...', sectionsCreated: 0 });
                  let extractFailed = false;

                  await generateFrameworkFromTender(
                    projectId,
                    docInfo.id,
                    (count) => {
                      setGenProgress({ phase: 'extract', message: `AI 抽取 ${count} 个章节模板中（约 30~60 秒）...`, sectionsCreated: 0 });
                    },
                    (matched, ms) => {
                      setGenProgress({ phase: 'create', message: `AI 抽取完成（命中 ${matched} 个，耗时 ${Math.round(ms / 1000)}s），正在创建章节...`, sectionsCreated: 0 });
                    },
                    (msg, ms) => {
                      extractFailed = true;
                      setGenProgress({ phase: 'create', message: `AI 抽取失败（${msg}，耗时 ${Math.round(ms / 1000)}s），降级创建空章节...`, sectionsCreated: 0 });
                    },
                    (_title, _type, _hasContent) => {
                      setGenProgress((prev) => prev ? { ...prev, sectionsCreated: prev.sectionsCreated + 1 } : prev);
                    },
                    (total, withContent) => {
                      setGenProgress({ phase: 'done', message: `已生成 ${total} 个章节（含模板 ${withContent} 个）`, sectionsCreated: total });
                      setGenerating(false);
                      if (extractFailed) {
                        message.warning(`已创建 ${total} 个空章节框架，AI 模板抽取失败请手动填写`);
                      } else {
                        message.success(`已生成 ${total} 个章节，其中 ${withContent} 个含招标文件模板原文`);
                      }
                      if (onFrameworkGenerated) onFrameworkGenerated(total, withContent);
                    },
                    (errMsg) => {
                      setGenerating(false);
                      setGenProgress(null);
                      message.error(`生成失败: ${errMsg}`);
                    },
                  );
                }}
              >
                {generating ? '生成中...' : '一键填入招标信息'}
              </Button>
```

- [ ] **Step 5: 在按钮所在的卡片下方追加进度面板**

在该 `<div>` 卡片闭合标签 `</div>` 之后、保存解析结果卡片 `<div>` 之前插入：

```typescript
          {genProgress && (
            <div style={{
              marginTop: 8,
              padding: '10px 14px',
              background: genProgress.phase === 'done' ? '#f0fdfa' : '#fef3c7',
              borderRadius: 6,
              border: `1px solid ${genProgress.phase === 'done' ? '#99f6e4' : '#fde68a'}`,
              fontSize: 12,
              color: '#475569',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {generating && <Spin size="small" />}
                <span>{genProgress.message}</span>
              </div>
              {genProgress.phase === 'create' && genProgress.sectionsCreated > 0 && (
                <div style={{ marginTop: 4, color: '#0d9488' }}>
                  已创建 {genProgress.sectionsCreated} 个章节
                </div>
              )}
            </div>
          )}
```

- [ ] **Step 6: 类型检查**

```bash
cd frontend && npx tsc --noEmit
```
Expected: 无新增错误

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/TenderDocParser/index.tsx
git commit -m "feat(bid): TenderDocParser button calls SSE framework generation with progress"
```

---

## Task 7: 前端 — Workbench 适配

**Files:**
- Modify: `frontend/src/pages/Bid/Workbench/index.tsx`

- [ ] **Step 1: 检查招标文件状态用于条件显示 fallback 按钮**

在组件状态区（约第 256 行 `setSections` 附近）追加：
```typescript
  const [hasTenderDoc, setHasTenderDoc] = useState(false);
```

在 `loadProject` 函数内部，调用 `getBidProject` 之后追加（确认是否已有解析过的招标文件）：
```typescript
  // 加载是否已有解析过的招标文件
  const loadHasTenderDoc = useCallback(async () => {
    if (!projectId) return;
    try {
      const { getTenderDocsByProject } = await import('@/services/tender_doc');
      const res = await getTenderDocsByProject(projectId);
      const docs = res.data || [];
      setHasTenderDoc(docs.some((d: TenderDocumentInfo) => d.parse_status === 'COMPLETED'));
    } catch {
      setHasTenderDoc(false);
    }
  }, [projectId]);
```

并在已有 useEffect 里追加调用：
```typescript
  useEffect(() => {
    loadProject();
    loadSections();
    loadHasTenderDoc();
  }, [loadProject, loadSections, loadHasTenderDoc]);
```

- [ ] **Step 2: 改造 fallback 按钮显示条件**

定位到「一键生成框架」按钮（当前约第 871-884 行），把外层条件 `{sections.length === 0 && (...)}` 改为：

```typescript
          {/* 一键生成框架按钮（仅在没有解析过招标文件、且章节数为 0 时显示） */}
          {sections.length === 0 && !hasTenderDoc && (
            <div style={{ padding: '4px 12px 8px', borderBottom: '1px solid #e2e8f0' }}>
              <Button
                type="dashed"
                block
                icon={<ThunderboltOutlined />}
                loading={frameworkLoading}
                onClick={handleGenerateFramework}
                style={{ color: '#0d9488', borderColor: '#0d9488' }}
              >
                一键生成框架（标准模板）
              </Button>
            </div>
          )}
```

- [ ] **Step 3: 改造 TenderDocParser 的回调**

定位到 `<TenderDocParser projectId={...} tenderId={...} onParseComplete={...}>`（约第 1124-1153 行），整段替换为：

```typescript
        <TenderDocParser
          projectId={project?.id}
          tenderId={project?.tender_id}
          onFrameworkGenerated={async () => {
            const treeRes = await getSectionTree(projectId);
            setSections(treeRes.data);
            await loadHasTenderDoc();
            setParseDrawerOpen(false);
            // 默认选中第 1 章
            const flat = flattenSections(treeRes.data);
            if (flat.length > 0) setSelectedSection(flat[0]);
          }}
        />
```

注意：移除原 `onParseComplete` 内的 `Modal.confirm` + 循环 `createSection` 逻辑。

- [ ] **Step 4: 类型检查 + 构建**

```bash
cd frontend && npx tsc --noEmit && npm run build
```
Expected: 无错误，构建成功

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/Bid/Workbench/index.tsx
git commit -m "feat(bid): Workbench uses new framework-from-tender flow, fallback hidden when tender parsed"
```

---

## Task 8: 端到端页面验证（Playwright 或浏览器手动）

**Files:** 不修改

- [ ] **Step 1: 启动前后端**

终端 1：
```bash
cd backend && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```
终端 2：
```bash
cd frontend && npm run dev
```
Expected: 前端启动在 http://localhost:5180，后端 8002

- [ ] **Step 2: 浏览器打开标书工作台**

访问 `http://localhost:5180/bid/list` → 选一个**已上传过招标文件**的项目进入工作台
Expected: 章节树为空（如果不为空，先全部删除或新建一个项目）

- [ ] **Step 3: 验证 fallback 按钮隐藏**

如果该项目已有解析过的招标文件，左侧栏「**一键生成框架（标准模板）**」按钮应该**不显示**
Expected: ✓ 按钮被隐藏

- [ ] **Step 4: 走"招标文件解析 + 一键填入"流程**

点击左侧「招标文件解析」打开 Drawer → 看到已有解析结果（或重新上传） → 滚到底部「解析到 N 个章节建议」卡片 → 点「一键填入招标信息」
Expected:
- 按钮变 loading 状态
- 下方进度面板出现，依次显示：
  - "AI 抽取 N 个章节模板中..."
  - "AI 抽取完成（命中 M 个），正在创建章节..."
  - "已生成 X 个章节（含模板 Y 个）"
- 最终关闭 Drawer，章节树刷新出来，自动选中第 1 章
- Toast 提示成功

- [ ] **Step 5: 验证生成的章节内容**

- 点开几个章节，看 `TEMPLATE` 类型章节是否有招标文件中的模板原文
- 末尾应该有「补充信息」章节（LIBRARY 类型）
- 必备 fallback（如"中小企业声明函"）若招标文件没识别，应该自动追加
Expected: ✓ 全部符合预期

- [ ] **Step 6: 回归 — 没解析过招标文件的项目**

新建一个没有上传招标文件的项目 → 进入工作台
Expected:
- 左侧「**一键生成框架（标准模板）**」按钮**显示**
- 点击后仍能用 25 章标准模板生成

- [ ] **Step 7: 回归 — 重复生成的拦截**

回到 Step 4 已生成过的项目，再点一次「一键填入招标信息」
Expected: Toast 错误提示"项目已有章节，请先清空再生成"

- [ ] **Step 8: 写测试报告**

新建 `docs/test-reports/2026-04-25-tender-template-extract-test-report.md`，记录：
- 各测试步骤结果
- 真实截图（如有）
- 发现的问题（如有）

提交：
```bash
git add docs/test-reports/2026-04-25-tender-template-extract-test-report.md
git commit -m "docs: add test report for tender template extract feature"
```

---

## Task 9: 文档更新与最终提交

**Files:**
- Modify: `CLAUDE.md`（追加近期更新记录）

- [ ] **Step 1: 更新 CLAUDE.md 近期更新记录**

打开 `CLAUDE.md`，在「### 近期更新记录（2026-04-15 ~ 2026-04-17）」标题更新为「2026-04-15 ~ 2026-04-25」，并在该章节末尾追加：

```markdown
#### 招标文件章节模板抽取（2026-04-25）
- 改造「一键填入招标信息」：解析招标文件后，AI 二次抽取每章对应的模板原文（响应函格式、报价表样式等），直接填入 section.content
- 后端：`tender_ai_parser.extract_chapter_templates()` + `bid_framework_service.generate_from_tender()`（SSE 流式）
- 章节合并规则：解析章节 + 必备 fallback（中小企业声明函等）+ 末尾「补充信息」章节
- 前端：`TenderDocParser` 进度面板 +`Workbench` 中「一键生成框架（标准模板）」按钮在已解析项目中隐藏
- 设计文档：`docs/superpowers/specs/2026-04-25-tender-template-extract-design.md`
- 实施计划：`docs/superpowers/plans/2026-04-25-tender-template-extract.md`
```

- [ ] **Step 2: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with tender template extract feature notes"
```

- [ ] **Step 3: 整体回顾**

```bash
git log --oneline -10
```
Expected: 看到本次 feature 的完整提交链路（约 7~9 个 commit）

---

## 完成标准

- [ ] 后端 `POST /api/v1/bid/projects/{id}/framework-from-tender` SSE 端点工作正常
- [ ] 用真实招标文件（如学院学生档案印刷服务）调一次，生成 7+ 章节，至少 3 个带模板原文
- [ ] 末尾自动追加「补充信息」LIBRARY 章节
- [ ] 必备章节（中小企业声明函等）若招标文件未列出会自动补
- [ ] 前端 TenderDocParser 按钮调用 SSE 显示进度，完成后自动刷新章节树+选中第 1 章
- [ ] Workbench 中「一键生成框架（标准模板）」按钮在已解析项目中隐藏
- [ ] AI 抽取失败能降级为创建空章节
- [ ] 重复生成有错误提示
- [ ] 测试报告已写
- [ ] CLAUDE.md 近期更新区已更新
