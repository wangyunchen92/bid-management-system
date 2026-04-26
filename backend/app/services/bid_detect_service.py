"""
标书检测服务 — 规则预检 + AI 逐类检测
"""
import json
import logging
import os
import re
from typing import AsyncGenerator, List, Optional

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.bid import BidProject, BidSection
from app.models.bid_check import BidCheckReport
from app.models.tender_document import TenderDocument

logger = logging.getLogger(__name__)

UPLOAD_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")

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
        "section_keywords": [],
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
        "section_keywords": [],
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

    # ── 规则预检 ──

    async def run_rule_checks(self, db: AsyncSession, project_id: int) -> list:
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
            attachments = re.findall(r'\[附件:([^:]+):([^\]]+)\]', content)
            for file_path, file_name in attachments:
                full_path = os.path.join(UPLOAD_BASE, file_path)
                if not os.path.exists(full_path):
                    items.append({
                        "category": "规则预检",
                        "check_name": "附件文件缺失",
                        "status": "FAIL",
                        "source": None,
                        "detail": f"「{s.title}」引用的附件「{file_name}」文件不存在",
                        "suggestion": "请在企业资料库中重新上传该附件",
                        "section_title": s.title,
                    })

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

    def _calc_rule_score(self, items: list) -> int:
        score = 100
        for item in items:
            if item["status"] == "FAIL":
                score -= 5
            elif item["status"] == "WARNING":
                score -= 2
        return max(0, score)

    # ── AI 逐类检测 ──

    async def _get_parse_result(self, db: AsyncSession, project_id: int) -> dict:
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
        keywords = category["section_keywords"]
        if not keywords:
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
                                   category: dict, sections: list, parse_result: dict) -> list:
        req_key = category["parse_key"]
        tender_req = parse_result.get(req_key, {})
        if isinstance(tender_req, (dict, list)):
            tender_req_text = json.dumps(tender_req, ensure_ascii=False, indent=2)
        else:
            tender_req_text = str(tender_req) if tender_req else "（未提取到该类别的招标要求）"

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
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                if text.endswith("```"):
                    text = text[:-3].strip()

            raw_items = json.loads(text)
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

    def _calc_ai_score(self, ai_items: list) -> int:
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
            total += int(rate * 20)
        return min(100, total)

    # ── 完整检测流程（SSE） ──

    async def run_detection_stream(self, db: AsyncSession, project_id: int, user_id: int) -> AsyncGenerator:
        sec_result = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project_id, BidSection.is_deleted == 0,
            ).order_by(BidSection.sort_order.asc())
        )
        sections = sec_result.scalars().all()
        parse_result = await self._get_parse_result(db, project_id)

        # 第一层：规则预检
        yield {"type": "rule_start"}
        rule_items = await self.run_rule_checks(db, project_id)
        rule_score = self._calc_rule_score(rule_items)
        for item in rule_items:
            yield {"type": "rule_item", "item": item}
        yield {"type": "rule_done", "rule_score": rule_score, "count": len(rule_items)}

        # 第二层：AI 逐类检测
        all_ai_items = []
        for i, category in enumerate(AI_CATEGORIES):
            yield {"type": "ai_start", "category": category["name"], "current": i + 1, "total": len(AI_CATEGORIES)}
            cat_items = await self.run_single_ai_check(db, project_id, category, sections, parse_result)
            all_ai_items.extend(cat_items)
            for item in cat_items:
                yield {"type": "ai_item", "item": item}
            cat_pass = sum(1 for it in cat_items if it.get("status") == "PASS")
            cat_score = int(cat_pass / len(cat_items) * 20) if cat_items else 0
            yield {"type": "ai_category_done", "category": category["name"], "score": cat_score}

        ai_score = self._calc_ai_score(all_ai_items)
        total_score = int(rule_score * 0.4 + ai_score * 0.6)
        status = "PASS" if total_score >= 80 else "WARNING" if total_score >= 60 else "FAIL"

        # 生成总评
        fail_count = sum(1 for i in rule_items + all_ai_items if i.get("status") == "FAIL")
        warn_count = sum(1 for i in rule_items + all_ai_items if i.get("status") in ("WARNING", "WARN"))
        pass_count = sum(1 for i in rule_items + all_ai_items if i.get("status") == "PASS")

        if fail_count == 0 and warn_count == 0:
            summary = f"标书整体合规，全部 {pass_count} 项检查通过，综合得分 {total_score} 分。"
        elif fail_count == 0:
            summary = f"标书基本合规，{pass_count} 项通过，{warn_count} 项需关注，综合得分 {total_score} 分。建议对警告项进行优化。"
        else:
            summary = f"标书存在 {fail_count} 项不合规风险，{warn_count} 项需关注，综合得分 {total_score} 分。请优先处理不合规项，避免废标。"

        # 保存报告
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
        await db.commit()
        await db.refresh(report)

        yield {
            "type": "done",
            "report_id": report.id,
            "total_score": total_score,
            "status": status,
            "summary": summary,
        }

    # ── 报告查询 ──

    async def get_reports(self, db: AsyncSession, project_id: int) -> list:
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

    async def get_report_detail(self, db: AsyncSession, report_id: int) -> Optional[dict]:
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
