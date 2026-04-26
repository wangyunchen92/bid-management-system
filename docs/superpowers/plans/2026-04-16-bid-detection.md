# AI 标书检测（A版）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有废标检查升级为"规则预检 + AI 逐类检测"双层架构，检测结果持久化，支持历史查看。

**Architecture:** 新增 BidCheckReport 模型存储检测报告。BidDetectService 负责规则预检（不调AI）和 AI 逐类检测（5轮独立调用）。SSE 流式推送检测进度。前端替换原废标检查 UI 为分类 Tab 报告展示。

**Tech Stack:** FastAPI + SQLAlchemy + OpenAI API（后端），React + Ant Design Tabs/Drawer（前端）

---

## File Structure

### 新建文件

| 文件 | 职责 |
|---|---|
| `backend/app/models/bid_check.py` | BidCheckReport ORM 模型 |
| `backend/app/schemas/bid_check.py` | 检测相关 Pydantic Schema |
| `backend/app/services/bid_detect_service.py` | 检测服务（规则预检 + AI 逐类检测 + 保存报告） |
| `backend/app/routers/bid_detect.py` | 检测路由（/detect, /detect/reports） |

### 修改文件

| 文件 | 改动 |
|---|---|
| `backend/app/main.py` | 注册 bid_detect 路由 |
| `frontend/src/constants/api.ts` | 新增 DETECT 相关 API 常量 |
| `frontend/src/services/bid.ts` | 新增检测相关 API 函数 |
| `frontend/src/pages/Bid/Workbench/index.tsx` | 替换废标检查按钮和 Drawer 为标书检测 UI |

---

### Task 1: 数据模型 — BidCheckReport

**Files:**
- Create: `backend/app/models/bid_check.py`

- [ ] **Step 1: 创建 BidCheckReport 模型**

```python
# backend/app/models/bid_check.py
"""标书检测报告模型"""

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BidCheckReport(BaseModel):
    """标书检测报告表"""
    __tablename__ = "bid_check_report"

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PASS")
    rule_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    ai_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_items: Mapped[str] = mapped_column(Text, nullable=True)  # JSON
    ai_items: Mapped[str] = mapped_column(Text, nullable=True)    # JSON
    summary: Mapped[str] = mapped_column(Text, nullable=True)
```

- [ ] **Step 2: 验证模型可导入**

Run: `cd backend && python3 -c "from app.models.bid_check import BidCheckReport; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 注册模型到 database（确保建表）**

模型继承 BaseModel → Base，init_db() 时 `Base.metadata.create_all` 会自动建表。验证：

Run: `cd backend && python3 -c "from app.database import Base; from app.models.bid_check import BidCheckReport; print([t for t in Base.metadata.tables if 'check' in t])"`
Expected: `['bid_check_report']`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/bid_check.py
git commit -m "feat(detect): add BidCheckReport model"
```

---

### Task 2: Schema — 检测请求和响应

**Files:**
- Create: `backend/app/schemas/bid_check.py`

- [ ] **Step 1: 创建检测相关 Schema**

```python
# backend/app/schemas/bid_check.py
"""标书检测 Schema"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DetectItem(BaseModel):
    """单条检查项"""
    category: str = Field(..., description="检查类别")
    check_name: str = Field(..., description="检查项名称")
    status: str = Field(..., description="PASS / WARNING / FAIL")
    source: Optional[str] = Field(default=None, description="招标文件依据引用")
    detail: str = Field(..., description="检查结果说明")
    suggestion: Optional[str] = Field(default=None, description="改进建议")
    section_title: Optional[str] = Field(default=None, description="关联的标书章节")


class DetectReportResponse(BaseModel):
    """检测报告完整响应"""
    id: int
    project_id: int
    total_score: int = 0
    status: str = "PASS"
    rule_score: int = 100
    ai_score: int = 0
    rule_items: List[DetectItem] = []
    ai_items: List[DetectItem] = []
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None


class DetectReportListItem(BaseModel):
    """检测报告列表项"""
    id: int
    total_score: int = 0
    status: str = "PASS"
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
```

- [ ] **Step 2: 验证 Schema 可导入**

Run: `cd backend && python3 -c "from app.schemas.bid_check import DetectItem, DetectReportResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/bid_check.py
git commit -m "feat(detect): add detection schemas"
```

---

### Task 3: 检测服务 — 规则预检 + AI 逐类检测

**Files:**
- Create: `backend/app/services/bid_detect_service.py`

- [ ] **Step 1: 创建检测服务骨架和规则预检**

```python
# backend/app/services/bid_detect_service.py
"""
标书检测服务 — 规则预检 + AI 逐类检测
"""
import json
import logging
import os
from typing import AsyncGenerator, List

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.bid import BidProject, BidSection
from app.models.bid_check import BidCheckReport
from app.models.tender_document import TenderDocument

logger = logging.getLogger(__name__)

UPLOAD_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")

# AI 检测的 5 个类别
AI_CATEGORIES = [
    {
        "name": "资格条件",
        "parse_key": "qualification",
        "section_keywords": ["资质", "营业执照", "业绩", "人员", "财务", "证明", "证书"],
        "description": "检查供应商资质、业绩、人员配备、财务状况是否满足招标要求",
    },
    {
        "name": "评分覆盖",
        "parse_key": "scoring",
        "section_keywords": [],  # 用全部章节标题
        "description": "检查招标评分标准中的每个得分项是否在标书中有对应内容",
    },
    {
        "name": "技术响应",
        "parse_key": "bid_document_requirements",
        "section_keywords": ["方案", "工艺", "质量", "进度", "保密", "环保", "安全", "售后", "服务"],
        "description": "检查技术参数和服务要求是否逐条响应",
    },
    {
        "name": "商务风险",
        "parse_key": "basic_info",
        "section_keywords": ["偏离", "报价", "商务"],
        "description": "检查偏离表中是否有实质性偏离导致废标风险",
    },
    {
        "name": "格式合规",
        "parse_key": "bid_document_requirements",
        "section_keywords": [],  # 用全部章节结构
        "description": "检查份数、装订、密封、签章等格式要求",
    },
]


class BidDetectService:

    def __init__(self):
        self._client = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=settings.AI_API_KEY, base_url=settings.AI_BASE_URL)
        return self._client

    # ── 规则预检 ──────────────────────────────────────────────

    async def run_rule_checks(self, db: AsyncSession, project_id: int) -> list[dict]:
        """规则预检：不调 AI，直接检查章节数据"""
        result = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project_id,
                BidSection.is_deleted == 0,
            ).order_by(BidSection.sort_order.asc())
        )
        sections = result.scalars().all()
        items = []

        for s in sections:
            content = s.content or ""
            content_len = len(content.strip())

            # 1. 空章节检查
            if content_len == 0:
                severity = "FAIL" if s.section_type in ("TEMPLATE", "LIBRARY") else "WARNING"
                items.append({
                    "category": "规则预检",
                    "check_name": "章节内容为空",
                    "status": severity,
                    "source": None,
                    "detail": f"「{s.title}」（{s.section_type}类型）内容为空",
                    "suggestion": {
                        "TEMPLATE": "请检查知识库是否有对应模板，或重新生成框架",
                        "LIBRARY": "请在企业资料库维护数据后，点击「填充资料库」",
                        "MANUAL": "请手动填写该章节内容",
                        "AI_GENERATE": "请点击「AI生成」或「批量AI生成」生成内容",
                    }.get(s.section_type, "请填写该章节内容"),
                    "section_title": s.title,
                })
                continue

            # 2. 字数不足（技术方案类 < 500 字）
            if s.section_type == "AI_GENERATE" and content_len < 500:
                items.append({
                    "category": "规则预检",
                    "check_name": "章节内容过少",
                    "status": "WARNING",
                    "source": None,
                    "detail": f"「{s.title}」仅 {content_len} 字，建议技术方案类章节不少于 500 字",
                    "suggestion": "内容过少可能导致评分偏低，建议补充完善或重新 AI 生成",
                    "section_title": s.title,
                })

            # 3. 签章落款检查（TEMPLATE 章节）
            if s.section_type == "TEMPLATE":
                has_seal = any(kw in content for kw in ["盖章", "签章", "签字", "（章）"])
                if not has_seal:
                    items.append({
                        "category": "规则预检",
                        "check_name": "缺少签章位置",
                        "status": "WARNING",
                        "source": None,
                        "detail": f"「{s.title}」未检测到盖章/签章标识",
                        "suggestion": "格式文件通常需要签章落款，请确认是否需要补充",
                        "section_title": s.title,
                    })

            # 4. 附件完整性检查
            import re
            attachments = re.findall(r'\[附件:([^:]+):([^\]]+)\]', content)
            for file_path, file_name in attachments:
                full_path = os.path.join(UPLOAD_BASE, file_path)
                if not os.path.exists(full_path):
                    items.append({
                        "category": "规则预检",
                        "check_name": "附件文件缺失",
                        "status": "FAIL",
                        "source": None,
                        "detail": f"「{s.title}」引用的附件「{file_name}」文件不存在：{file_path}",
                        "suggestion": "请在企业资料库中重新上传该附件",
                        "section_title": s.title,
                    })

        # 如果全部通过
        if not items:
            items.append({
                "category": "规则预检",
                "check_name": "基础检查全部通过",
                "status": "PASS",
                "source": None,
                "detail": f"全部 {len(sections)} 个章节均已填写，格式完整",
                "suggestion": None,
                "section_title": None,
            })

        return items

    def _calc_rule_score(self, items: list[dict]) -> int:
        """根据规则预检结果计算得分（100分起扣）"""
        score = 100
        for item in items:
            if item["status"] == "FAIL":
                score -= 5
            elif item["status"] == "WARNING":
                score -= 2
        return max(0, score)

    # ── AI 逐类检测 ──────────────────────────────────────────

    async def _get_parse_result(self, db: AsyncSession, project_id: int) -> dict:
        """获取招标文件解析结果 JSON"""
        doc_result = await db.execute(
            select(TenderDocument).where(
                TenderDocument.project_id == project_id,
                TenderDocument.parse_status == "COMPLETED",
                TenderDocument.is_deleted == 0,
            ).order_by(TenderDocument.id.desc()).limit(1)
        )
        doc = doc_result.scalar_one_or_none()
        if doc and doc.parse_result:
            try:
                return json.loads(doc.parse_result) if isinstance(doc.parse_result, str) else doc.parse_result
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    def _get_sections_for_category(self, sections: list, category: dict) -> str:
        """根据类别关键词筛选相关章节内容"""
        keywords = category["section_keywords"]
        if not keywords:
            # 无关键词 = 用全部章节
            parts = []
            for s in sections:
                content_preview = (s.content or "（未填写）")[:2000]
                parts.append(f"### {s.title} [{s.section_type}]\n{content_preview}")
            return "\n\n".join(parts)

        parts = []
        for s in sections:
            if any(kw in s.title for kw in keywords):
                content = s.content or "（未填写）"
                parts.append(f"### {s.title}\n{content}")
        return "\n\n".join(parts) if parts else "（无相关章节内容）"

    async def run_single_ai_check(self, db: AsyncSession, project_id: int,
                                   category: dict, sections: list, parse_result: dict) -> list[dict]:
        """对单个类别执行 AI 检测"""
        # 提取该类别对应的招标要求
        req_key = category["parse_key"]
        tender_req = parse_result.get(req_key, {})
        if isinstance(tender_req, dict):
            tender_req_text = json.dumps(tender_req, ensure_ascii=False, indent=2)
        elif isinstance(tender_req, list):
            tender_req_text = json.dumps(tender_req, ensure_ascii=False, indent=2)
        else:
            tender_req_text = str(tender_req) if tender_req else "（未提取到该类别的招标要求）"

        # 筛选相关章节
        bid_content = self._get_sections_for_category(sections, category)

        prompt = f"""你是政府采购标书合规性检测专家。

当前检测类别：{category["name"]}
检测说明：{category["description"]}

招标文件要求：
{tender_req_text}

标书对应内容：
{bid_content}

请逐条检查标书是否满足招标要求，返回 JSON 数组（不要 ```json 包裹）：
[
  {{
    "check_name": "检查项名称",
    "status": "PASS/WARNING/FAIL",
    "source": "招标文件原文要求（引用）",
    "detail": "检查结果说明",
    "suggestion": "改进建议（PASS时为null）"
  }}
]

检查原则：
1. 每条必须引用招标文件原文作为依据
2. FAIL = 可能导致废标的硬伤
3. WARNING = 有风险但不一定废标
4. PASS = 明确满足要求
5. 宁严勿松，有疑问判 WARNING
6. 至少检查 3 条以上"""

        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=settings.AI_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个严谨的政府采购标书合规性检测专家。只返回JSON数组，不要其他文字。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0.1,
            )
            text = response.choices[0].message.content.strip()
            # 清理 markdown 包裹
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                if text.endswith("```"):
                    text = text[:-3].strip()

            raw_items = json.loads(text)
            # 补充 category 字段
            for item in raw_items:
                item["category"] = category["name"]
                item.setdefault("section_title", None)
            return raw_items
        except Exception as e:
            logger.error(f"AI检测失败 [{category['name']}]: {e}")
            return [{
                "category": category["name"],
                "check_name": f"{category['name']}检测失败",
                "status": "WARNING",
                "source": None,
                "detail": f"AI 调用异常：{str(e)[:100]}",
                "suggestion": "请稍后重试",
                "section_title": None,
            }]

    def _calc_ai_score(self, ai_items: list[dict]) -> int:
        """AI 检测得分：5个类别各20分，按通过率计算"""
        category_scores = {}
        for item in ai_items:
            cat = item.get("category", "其他")
            if cat not in category_scores:
                category_scores[cat] = {"total": 0, "pass": 0}
            category_scores[cat]["total"] += 1
            if item.get("status") == "PASS":
                category_scores[cat]["pass"] += 1

        total = 0
        for cat_name in [c["name"] for c in AI_CATEGORIES]:
            stats = category_scores.get(cat_name, {"total": 1, "pass": 0})
            rate = stats["pass"] / stats["total"] if stats["total"] > 0 else 0
            total += int(rate * 20)  # 每类 20 分
        return min(100, total)

    # ── 完整检测流程（SSE） ──────────────────────────────────

    async def run_detection_stream(self, db: AsyncSession, project_id: int, user_id: int) -> AsyncGenerator:
        """流式执行完整检测，yield SSE 事件"""
        # 加载章节和解析结果
        sec_result = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project_id, BidSection.is_deleted == 0,
            ).order_by(BidSection.sort_order.asc())
        )
        sections = sec_result.scalars().all()
        parse_result = await self._get_parse_result(db, project_id)

        # ── 第一层：规则预检 ──
        yield {"type": "rule_start"}
        rule_items = await self.run_rule_checks(db, project_id)
        rule_score = self._calc_rule_score(rule_items)
        for item in rule_items:
            yield {"type": "rule_item", "item": item}
        yield {"type": "rule_done", "rule_score": rule_score, "count": len(rule_items)}

        # ── 第二层：AI 逐类检测 ──
        all_ai_items = []
        for i, category in enumerate(AI_CATEGORIES):
            yield {"type": "ai_start", "category": category["name"], "current": i + 1, "total": len(AI_CATEGORIES)}
            cat_items = await self.run_single_ai_check(db, project_id, category, sections, parse_result)
            all_ai_items.extend(cat_items)
            for item in cat_items:
                yield {"type": "ai_item", "item": item}
            # 计算该类别得分
            cat_pass = sum(1 for it in cat_items if it.get("status") == "PASS")
            cat_score = int(cat_pass / len(cat_items) * 20) if cat_items else 0
            yield {"type": "ai_category_done", "category": category["name"], "score": cat_score}

        ai_score = self._calc_ai_score(all_ai_items)

        # ── 计算综合得分 ──
        total_score = int(rule_score * 0.4 + ai_score * 0.6)
        status = "PASS" if total_score >= 80 else "WARNING" if total_score >= 60 else "FAIL"

        # 生成总评
        summary = await self._generate_summary(total_score, status, rule_items, all_ai_items)

        # ── 保存报告 ──
        report = BidCheckReport(
            project_id=project_id,
            total_score=total_score,
            status=status,
            rule_score=rule_score,
            ai_score=ai_score,
            rule_items=json.dumps(rule_items, ensure_ascii=False),
            ai_items=json.dumps(all_ai_items, ensure_ascii=False),
            summary=summary,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(report)
        await db.flush()
        await db.refresh(report)

        yield {
            "type": "done",
            "report_id": report.id,
            "total_score": total_score,
            "status": status,
            "summary": summary,
        }

    async def _generate_summary(self, score: int, status: str, rule_items: list, ai_items: list) -> str:
        """用 AI 生成一句话总评"""
        fail_count = sum(1 for i in rule_items + ai_items if i.get("status") == "FAIL")
        warn_count = sum(1 for i in rule_items + ai_items if i.get("status") in ("WARNING", "WARN"))
        pass_count = sum(1 for i in rule_items + ai_items if i.get("status") == "PASS")

        # 简单场景不调 AI
        if fail_count == 0 and warn_count == 0:
            return f"标书整体合规，全部 {pass_count} 项检查通过，综合得分 {score} 分。"
        if fail_count == 0:
            return f"标书基本合规，{pass_count} 项通过，{warn_count} 项需关注，综合得分 {score} 分。建议对警告项进行优化。"
        return f"标书存在 {fail_count} 项不合规风险，{warn_count} 项需关注，综合得分 {score} 分。请优先处理不合规项，避免废标。"

    # ── 报告查询 ──────────────────────────────────────────────

    async def get_reports(self, db: AsyncSession, project_id: int) -> list[dict]:
        """获取历史检测报告列表"""
        result = await db.execute(
            select(BidCheckReport).where(
                BidCheckReport.project_id == project_id,
                BidCheckReport.is_deleted == 0,
            ).order_by(BidCheckReport.id.desc()).limit(20)
        )
        reports = result.scalars().all()
        return [
            {
                "id": r.id,
                "total_score": r.total_score,
                "status": r.status,
                "summary": r.summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]

    async def get_report_detail(self, db: AsyncSession, report_id: int) -> dict | None:
        """获取单份报告详情"""
        result = await db.execute(
            select(BidCheckReport).where(
                BidCheckReport.id == report_id,
                BidCheckReport.is_deleted == 0,
            )
        )
        report = result.scalar_one_or_none()
        if not report:
            return None
        return {
            "id": report.id,
            "project_id": report.project_id,
            "total_score": report.total_score,
            "status": report.status,
            "rule_score": report.rule_score,
            "ai_score": report.ai_score,
            "rule_items": json.loads(report.rule_items) if report.rule_items else [],
            "ai_items": json.loads(report.ai_items) if report.ai_items else [],
            "summary": report.summary,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "created_by": report.created_by,
        }


bid_detect_service = BidDetectService()
```

- [ ] **Step 2: 验证服务可导入**

Run: `cd backend && python3 -c "from app.services.bid_detect_service import bid_detect_service; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/bid_detect_service.py
git commit -m "feat(detect): add BidDetectService with rule checks and AI detection"
```

---

### Task 4: 路由 — 检测 API

**Files:**
- Create: `backend/app/routers/bid_detect.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建检测路由**

```python
# backend/app/routers/bid_detect.py
"""标书检测路由 /api/v1/bid/"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id
from app.common.response import success
from app.services.bid_detect_service import bid_detect_service

router = APIRouter()


@router.post("/projects/{project_id}/detect", summary="标书检测（SSE流式）")
async def detect_bid(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """执行标书检测：规则预检 + AI逐类检测，SSE 流式推送进度"""
    async def event_generator():
        async for event in bid_detect_service.run_detection_stream(db, project_id, user_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/projects/{project_id}/detect/reports", summary="检测报告列表")
async def list_reports(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    reports = await bid_detect_service.get_reports(db, project_id)
    return success(data=reports)


@router.get("/projects/{project_id}/detect/reports/{report_id}", summary="检测报告详情")
async def get_report(
    project_id: int,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    report = await bid_detect_service.get_report_detail(db, report_id)
    if not report:
        raise Exception("检测报告不存在")
    return success(data=report)
```

- [ ] **Step 2: 在 main.py 注册路由**

在 `backend/app/main.py` 的 import 区域添加：

```python
from app.routers import bid_detect
```

在 `include_router` 区域（bid 路由后面）添加：

```python
app.include_router(bid_detect.router, prefix="/api/v1/bid", tags=["标书检测"])
```

- [ ] **Step 3: 验证路由注册成功**

Run: `cd backend && python3 -c "from app.main import app; routes = [r.path for r in app.routes]; print('/api/v1/bid/projects/{project_id}/detect' in routes)"`

- [ ] **Step 4: 用 curl 测试规则预检（SSE）**

Run:
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8004/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")

curl -N http://127.0.0.1:8004/api/v1/bid/projects/9/detect \
  -X POST -H "Authorization: Bearer $TOKEN" 2>&1 | head -20
```

Expected: 看到 `data: {"type": "rule_start"}` 和后续的 SSE 事件流。

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/bid_detect.py backend/app/main.py
git commit -m "feat(detect): add detection API routes with SSE streaming"
```

---

### Task 5: 前端 API 层

**Files:**
- Modify: `frontend/src/constants/api.ts`
- Modify: `frontend/src/services/bid.ts`

- [ ] **Step 1: 添加 API 常量**

在 `frontend/src/constants/api.ts` 的 `BID_API` 对象中添加：

```typescript
  // 标书检测
  PROJECT_DETECT: (projectId: number) => `${API_PREFIX}/bid/projects/${projectId}/detect`,
  PROJECT_DETECT_REPORTS: (projectId: number) => `${API_PREFIX}/bid/projects/${projectId}/detect/reports`,
  PROJECT_DETECT_REPORT_DETAIL: (projectId: number, reportId: number) => `${API_PREFIX}/bid/projects/${projectId}/detect/reports/${reportId}`,
```

- [ ] **Step 2: 添加 API 函数**

在 `frontend/src/services/bid.ts` 中添加：

```typescript
// ── 标书检测 ──────────────────────────────────────────────────

export interface DetectItem {
  category: string;
  check_name: string;
  status: 'PASS' | 'WARNING' | 'FAIL';
  source: string | null;
  detail: string;
  suggestion: string | null;
  section_title: string | null;
}

export interface DetectReport {
  id: number;
  project_id: number;
  total_score: number;
  status: string;
  rule_score: number;
  ai_score: number;
  rule_items: DetectItem[];
  ai_items: DetectItem[];
  summary: string | null;
  created_at: string | null;
  created_by: number | null;
}

export interface DetectReportListItem {
  id: number;
  total_score: number;
  status: string;
  summary: string | null;
  created_at: string | null;
}

export async function runBidDetection(
  projectId: number,
  onRuleItem: (item: DetectItem) => void,
  onRuleDone: (ruleScore: number, count: number) => void,
  onAiStart: (category: string, current: number, total: number) => void,
  onAiItem: (item: DetectItem) => void,
  onAiCategoryDone: (category: string, score: number) => void,
  onDone: (reportId: number, totalScore: number, status: string, summary: string) => void,
  onError: (err: string) => void,
) {
  const token = localStorage.getItem('bid_system_access_token');
  const response = await fetch(BID_API.PROJECT_DETECT(projectId), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
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
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          switch (data.type) {
            case 'rule_item': onRuleItem(data.item); break;
            case 'rule_done': onRuleDone(data.rule_score, data.count); break;
            case 'ai_start': onAiStart(data.category, data.current, data.total); break;
            case 'ai_item': onAiItem(data.item); break;
            case 'ai_category_done': onAiCategoryDone(data.category, data.score); break;
            case 'done': onDone(data.report_id, data.total_score, data.status, data.summary); break;
          }
        } catch { /* skip */ }
      }
    }
  }
}

export function getDetectReports(projectId: number) {
  return get<DetectReportListItem[]>(BID_API.PROJECT_DETECT_REPORTS(projectId));
}

export function getDetectReportDetail(projectId: number, reportId: number) {
  return get<DetectReport>(BID_API.PROJECT_DETECT_REPORT_DETAIL(projectId, reportId));
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/constants/api.ts frontend/src/services/bid.ts
git commit -m "feat(detect): add frontend API layer for detection"
```

---

### Task 6: 前端 UI — 替换废标检查为标书检测

**Files:**
- Modify: `frontend/src/pages/Bid/Workbench/index.tsx`

这是最大的改动。需要：
1. 替换按钮文字和点击逻辑
2. 删除旧的 checkInputOpen Modal
3. 重写 checkDrawer 内容为分类 Tab 报告

- [ ] **Step 1: 添加 import 和新状态**

在 import 区域添加 `Tabs` 组件和新 API 函数：

```typescript
// antd import 中添加 Tabs
import { ..., Tabs } from 'antd';

// services/bid import 中添加
import { ..., runBidDetection, getDetectReports, getDetectReportDetail } from '@/services/bid';
import type { DetectItem, DetectReport, DetectReportListItem } from '@/services/bid';
```

替换旧的废标检查状态为新状态：

```typescript
// 删除这些旧状态：
// const [checkDrawerOpen, setCheckDrawerOpen] = useState(false);
// const [checkLoading, setCheckLoading] = useState(false);
// const [checkResult, setCheckResult] = useState<BidCheckResult | null>(null);
// const [checkTenderReq, setCheckTenderReq] = useState('');
// const [checkInputOpen, setCheckInputOpen] = useState(false);

// 替换为新状态：
const [detectDrawerOpen, setDetectDrawerOpen] = useState(false);
const [detectLoading, setDetectLoading] = useState(false);
const [detectProgress, setDetectProgress] = useState('');
const [detectReport, setDetectReport] = useState<DetectReport | null>(null);
const [detectHistory, setDetectHistory] = useState<DetectReportListItem[]>([]);
```

- [ ] **Step 2: 添加检测处理函数**

替换旧的 `handleComplianceCheck` 为：

```typescript
const handleDetect = async () => {
  setDetectDrawerOpen(true);
  setDetectLoading(true);
  setDetectProgress('正在进行规则预检...');

  const ruleItems: DetectItem[] = [];
  const aiItems: DetectItem[] = [];
  let ruleScore = 100;
  let aiScore = 0;

  await runBidDetection(
    projectId,
    (item) => { ruleItems.push(item); },
    (score, count) => {
      ruleScore = score;
      setDetectProgress(`规则预检完成（${count}项），开始 AI 检测...`);
    },
    (category, current, total) => {
      setDetectProgress(`AI 检测中：${category}（${current}/${total}）`);
    },
    (item) => { aiItems.push(item); },
    (category, score) => { aiScore += score; },
    (reportId, totalScore, status, summary) => {
      setDetectReport({
        id: reportId,
        project_id: projectId,
        total_score: totalScore,
        status,
        rule_score: ruleScore,
        ai_score: aiScore,
        rule_items: ruleItems,
        ai_items: aiItems,
        summary,
        created_at: new Date().toISOString(),
        created_by: null,
      });
      setDetectLoading(false);
      // 加载历史记录
      getDetectReports(projectId).then(res => setDetectHistory(res.data || []));
    },
    (err) => {
      message.error(`检测失败: ${err}`);
      setDetectLoading(false);
    },
  );
};

const handleLoadHistoryReport = async (reportId: number) => {
  try {
    const res = await getDetectReportDetail(projectId, reportId);
    setDetectReport(res.data);
  } catch {
    message.error('加载报告失败');
  }
};
```

- [ ] **Step 3: 替换工具栏按钮**

将旧的废标检查按钮：

```tsx
<Button
  icon={<SafetyCertificateOutlined />}
  onClick={() => setCheckInputOpen(true)}
  style={{ color: '#d97706', borderColor: '#d97706' }}
>
  废标检查
</Button>
```

替换为：

```tsx
<Button
  icon={<SafetyCertificateOutlined />}
  loading={detectLoading}
  onClick={handleDetect}
  style={{ color: '#d97706', borderColor: '#d97706' }}
>
  标书检测
</Button>
```

- [ ] **Step 4: 替换废标检查输入 Modal 和结果 Drawer**

删除旧的"废标检查 - 输入 Modal"和"废标检查结果 Drawer"两个组件块。

替换为新的检测 Drawer：

```tsx
{/* 标书检测 Drawer */}
<Drawer
  title={
    <Space>
      <SafetyCertificateOutlined style={{ color: '#d97706' }} />
      标书检测报告
    </Space>
  }
  placement="right"
  width={720}
  open={detectDrawerOpen}
  onClose={() => setDetectDrawerOpen(false)}
>
  {detectLoading ? (
    <div style={{ textAlign: 'center', padding: 60 }}>
      <Spin size="large" />
      <div style={{ marginTop: 16, color: '#64748b', fontSize: 14 }}>{detectProgress}</div>
    </div>
  ) : detectReport ? (
    <div>
      {/* 总览卡片 */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 24,
        padding: '20px 0', borderBottom: '1px solid #e2e8f0', marginBottom: 16,
      }}>
        <Progress
          type="circle"
          percent={detectReport.total_score}
          size={90}
          strokeColor={detectReport.total_score >= 80 ? '#22c55e' : detectReport.total_score >= 60 ? '#f59e0b' : '#ef4444'}
          format={(pct) => <span style={{ fontSize: 20, fontWeight: 700 }}>{pct}</span>}
        />
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 8 }}>
            <Tag color={detectReport.status === 'PASS' ? 'success' : detectReport.status === 'WARNING' ? 'warning' : 'error'} style={{ fontSize: 14, padding: '2px 12px' }}>
              {detectReport.status === 'PASS' ? '通过' : detectReport.status === 'WARNING' ? '需关注' : '不合规'}
            </Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>规则 {detectReport.rule_score}分 | AI {detectReport.ai_score}分</Text>
          </div>
          <div style={{ fontSize: 13, color: '#475569' }}>{detectReport.summary}</div>
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12 }}>
            <span style={{ color: '#22c55e' }}>✅ {[...detectReport.rule_items, ...detectReport.ai_items].filter(i => i.status === 'PASS').length}</span>
            <span style={{ color: '#f59e0b' }}>⚠️ {[...detectReport.rule_items, ...detectReport.ai_items].filter(i => i.status === 'WARNING').length}</span>
            <span style={{ color: '#ef4444' }}>❌ {[...detectReport.rule_items, ...detectReport.ai_items].filter(i => i.status === 'FAIL').length}</span>
          </div>
        </div>
      </div>

      {/* 分类 Tab */}
      <Tabs
        size="small"
        items={[
          {
            key: 'all',
            label: '全部',
            children: renderDetectItems([...detectReport.rule_items, ...detectReport.ai_items]
              .sort((a, b) => {
                const order: Record<string, number> = { FAIL: 0, WARNING: 1, PASS: 2 };
                return (order[a.status] ?? 3) - (order[b.status] ?? 3);
              })),
          },
          { key: 'rule', label: '规则预检', children: renderDetectItems(detectReport.rule_items) },
          { key: 'qualification', label: '资格条件', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '资格条件')) },
          { key: 'scoring', label: '评分覆盖', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '评分覆盖')) },
          { key: 'tech', label: '技术响应', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '技术响应')) },
          { key: 'commercial', label: '商务风险', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '商务风险')) },
          { key: 'format', label: '格式合规', children: renderDetectItems(detectReport.ai_items.filter(i => i.category === '格式合规')) },
        ]}
      />

      {/* 历史记录 */}
      {detectHistory.length > 1 && (
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e2e8f0' }}>
          <Text strong style={{ fontSize: 13, color: '#475569' }}>历史检测</Text>
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {detectHistory.map(h => (
              <div
                key={h.id}
                onClick={() => handleLoadHistoryReport(h.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 10px', borderRadius: 6, cursor: 'pointer',
                  background: h.id === detectReport.id ? '#f0fdfa' : '#f8fafc',
                  border: h.id === detectReport.id ? '1px solid #99f6e4' : '1px solid #e2e8f0',
                }}
              >
                <Tag color={h.status === 'PASS' ? 'success' : h.status === 'WARNING' ? 'warning' : 'error'} style={{ fontSize: 11 }}>
                  {h.total_score}分
                </Tag>
                <Text style={{ fontSize: 12, flex: 1 }} ellipsis>{h.summary}</Text>
                <Text type="secondary" style={{ fontSize: 11 }}>{h.created_at?.slice(0, 16).replace('T', ' ')}</Text>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  ) : (
    <Empty description="暂无检测结果" />
  )}
</Drawer>
```

- [ ] **Step 5: 添加 renderDetectItems 辅助函数**

在组件内（return 之前）添加：

```typescript
const renderDetectItems = (items: DetectItem[]) => {
  if (!items.length) return <Empty description="此类别暂无检查项" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  return (
    <List
      size="small"
      dataSource={items}
      renderItem={(item) => {
        const icon = item.status === 'PASS'
          ? <CheckCircleFilled style={{ color: '#22c55e', fontSize: 16 }} />
          : item.status === 'WARNING'
          ? <WarningFilled style={{ color: '#f59e0b', fontSize: 16 }} />
          : <CloseCircleFilled style={{ color: '#ef4444', fontSize: 16 }} />;
        return (
          <List.Item style={{ alignItems: 'flex-start', padding: '10px 0' }}>
            <div style={{ display: 'flex', gap: 10, width: '100%' }}>
              <div style={{ marginTop: 2, flexShrink: 0 }}>{icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: 2, fontSize: 13 }}>{item.check_name}</div>
                {item.source && (
                  <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 2 }}>依据：{item.source}</div>
                )}
                <div style={{ fontSize: 13, color: '#475569', marginBottom: item.suggestion ? 4 : 0 }}>{item.detail}</div>
                {item.suggestion && (
                  <div style={{
                    fontSize: 12, color: '#6d28d9', background: '#f5f3ff',
                    padding: '4px 8px', borderRadius: 4, borderLeft: '3px solid #8b5cf6', marginTop: 4,
                  }}>
                    建议：{item.suggestion}
                  </div>
                )}
                {item.section_title && (
                  <Text type="secondary" style={{ fontSize: 11 }}>章节：{item.section_title}</Text>
                )}
              </div>
            </div>
          </List.Item>
        );
      }}
    />
  );
};
```

- [ ] **Step 6: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Bid/Workbench/index.tsx
git commit -m "feat(detect): replace compliance check UI with structured detection report"
```

---

### Task 7: 集成验证与部署

- [ ] **Step 1: 本地启动后端验证**

Run: `cd backend && python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002`

验证：`curl -s http://127.0.0.1:8002/api/docs | grep detect`
Expected: 看到 `/detect` 相关路由

- [ ] **Step 2: 本地前端验证**

Run: `cd frontend && npm run dev`

打开浏览器访问工作台，确认：
- 按钮显示「标书检测」
- 点击后 Drawer 打开，显示进度
- 检测完成后显示分类 Tab 报告

- [ ] **Step 3: 打包前端**

Run: `cd frontend && npm run build`
Expected: 无报错

- [ ] **Step 4: 部署到服务器**

```bash
# 上传后端
rsync -avz --delete \
  --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  --exclude 'venv' --exclude '.venv' --exclude 'data/uploads' --exclude 'data/bid.db' \
  backend/ root@118.31.237.111:/opt/bid-system/backend/

# 上传前端
rsync -avz --delete \
  frontend/dist/ root@118.31.237.111:/opt/bid-system/www/bid/

# 重启后端
ssh root@118.31.237.111 "systemctl restart bid-system"
```

- [ ] **Step 5: 线上验证**

打开 http://118.31.237.111/bid/，进入标书工作台，点击「标书检测」，确认完整流程正常。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(detect): bid detection A-version complete"
```
