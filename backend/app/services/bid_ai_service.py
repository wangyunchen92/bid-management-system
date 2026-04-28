"""
标书 AI 服务 — 内容生成 + 废标检查
"""
import json
import logging
from typing import Optional

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.bid import BidProject, BidSection
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.models.library import Qualification, Achievement, PersonnelCert, Product
from app.models.knowledge import KnowledgeTemplate

logger = logging.getLogger(__name__)


class BidAIService:

    def __init__(self):
        self.client = None

    def _get_client(self) -> OpenAI:
        if self.client is None:
            self.client = OpenAI(api_key=settings.AI_API_KEY, base_url=settings.AI_BASE_URL)
        return self.client

    async def _get_company_info(self, db: AsyncSession) -> str:
        """获取企业资料库摘要，作为 AI 上下文"""
        parts = []

        # 资质证书
        result = await db.execute(select(Qualification).where(Qualification.is_deleted == 0).limit(20))
        quals = result.scalars().all()
        if quals:
            parts.append("【企业资质】")
            for q in quals:
                parts.append(f"- {q.cert_name}（{q.cert_type or ''}，编号：{q.cert_no or ''}）")

        # 业绩案例（含描述和完成时间）
        result = await db.execute(select(Achievement).where(Achievement.is_deleted == 0).limit(10))
        achvs = result.scalars().all()
        if achvs:
            parts.append("\n【业绩案例】")
            for a in achvs:
                amount = f"，合同金额{float(a.contract_amount)}万元" if a.contract_amount else ""
                date = f"，完成时间{a.completion_date.strftime('%Y年%m月') if a.completion_date else ''}" if a.completion_date else ""
                desc = f"，项目内容：{a.description}" if a.description else ""
                has_proof = "，有合同证明材料" if a.file_path else ""
                parts.append(f"- {a.project_name}（甲方：{a.client_name or ''}{amount}{date}{desc}{has_proof}）")

        # 人员证书
        result = await db.execute(select(PersonnelCert).where(PersonnelCert.is_deleted == 0).limit(20))
        certs = result.scalars().all()
        if certs:
            parts.append("\n【人员证书】")
            for c in certs:
                parts.append(f"- {c.person_name}：{c.cert_name}（{c.cert_no or ''}）")

        # 产品/设备
        result = await db.execute(select(Product).where(Product.is_deleted == 0).limit(10))
        prods = result.scalars().all()
        if prods:
            parts.append("\n【产品/设备】")
            for p in prods:
                parts.append(f"- {p.name}（{p.brand or ''} {p.model or ''}，数量：{p.quantity}）")

        return "\n".join(parts) if parts else "（企业资料库暂无数据）"

    async def _get_tender_requirements(self, db: AsyncSession, project_id: int) -> str:
        """获取招标要求（从解析结果中提取）"""
        # 先找项目关联的招标
        project_result = await db.execute(select(BidProject).where(BidProject.id == project_id))
        project = project_result.scalar_one_or_none()
        if not project:
            return ""

        # 查找解析过的招标文件
        doc_result = await db.execute(
            select(TenderDocument).where(
                TenderDocument.project_id == project_id,
                TenderDocument.parse_status == "COMPLETED",
                TenderDocument.is_deleted == 0,
            ).order_by(TenderDocument.id.desc()).limit(1)
        )
        doc = doc_result.scalar_one_or_none()
        if doc and doc.parse_result:
            return f"【招标文件解析结果】\n{doc.parse_result}"

        # 没有解析结果，尝试从招标信息获取基本信息
        if project.tender_id:
            tender_result = await db.execute(select(Tender).where(Tender.id == project.tender_id))
            tender = tender_result.scalar_one_or_none()
            if tender:
                return f"【招标基本信息】\n项目名称：{tender.title}\n招标编号：{tender.tender_no or ''}\n招标单位：{tender.tender_unit or ''}\n预算金额：{float(tender.budget_amount) if tender.budget_amount else '未知'}万元"

        return ""

    async def _get_knowledge_reference(self, db: AsyncSession, section_title: str) -> str:
        """从知识库搜索与当前章节相关的模板，作为参考"""
        from sqlalchemy import or_

        # 用章节标题关键词搜索知识库
        keywords = [w for w in section_title.replace('第', '').replace('章', '').replace('节', '').split() if len(w) > 1]
        if not keywords:
            keywords = [section_title]

        query = select(KnowledgeTemplate).where(KnowledgeTemplate.is_deleted == 0)
        conditions = []
        for kw in keywords[:3]:  # 最多3个关键词
            conditions.append(KnowledgeTemplate.title.contains(kw))
            conditions.append(KnowledgeTemplate.tags.contains(kw))
        if conditions:
            query = query.where(or_(*conditions))
        query = query.order_by(KnowledgeTemplate.usage_count.desc()).limit(3)

        result = await db.execute(query)
        templates = result.scalars().all()

        if not templates:
            return ""

        parts = ["【知识库参考模板】"]
        for t in templates:
            # 截取前500字作为参考
            content_preview = t.content[:500] if t.content else ""
            parts.append(f"\n--- 模板：{t.title} ---")
            parts.append(content_preview)
            if t.content and len(t.content) > 500:
                parts.append("...(已截取前500字)")

        return "\n".join(parts)

    async def _get_scoring_items_for_section(self, db: AsyncSession, section_id: int) -> str:
        """获取章节关联的评分项，格式化为 prompt 片段（链路 B v1）"""
        from app.models.bid import BidScoringItem, BidSectionScoringItem
        res = await db.execute(
            select(BidScoringItem)
            .join(BidSectionScoringItem, BidSectionScoringItem.scoring_item_id == BidScoringItem.id)
            .where(BidSectionScoringItem.section_id == section_id, BidScoringItem.is_deleted == 0)
            .order_by(BidSectionScoringItem.sort_order, BidScoringItem.sort_order)
        )
        items = res.scalars().all()
        if not items:
            return ""
        lines = ["【关联评分项 — 这是拿分关键，请逐条响应】"]
        total = 0
        for it in items:
            score_str = f"满分 {float(it.max_score)} 分" if it.max_score is not None else "分值未明"
            if it.max_score is not None:
                total += float(it.max_score)
            lines.append(f"\n▶ {it.item_name}（{score_str}，类别：{it.category}）")
            lines.append(f"  评分细则：{it.criteria}")
            if it.required_evidence:
                lines.append(f"  需要的证据：{it.required_evidence}")
        if total > 0:
            lines.insert(1, f"（本章节合计 {total} 分，请确保拿满）")
        return "\n".join(lines)

    async def _get_other_sections_context(self, db: AsyncSession, project_id: int, current_section_id: int) -> str:
        """获取其他章节的标题和摘要，提供上下文"""
        result = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project_id, BidSection.is_deleted == 0
            ).order_by(BidSection.sort_order.asc())
        )
        sections = result.scalars().all()
        parts = ["【标书章节结构】"]
        for s in sections:
            marker = "→ " if s.id == current_section_id else "  "
            status = "（当前章节，需要生成内容）" if s.id == current_section_id else ""
            preview = ""
            if s.content and s.id != current_section_id:
                preview = f" — {s.content[:50]}..."
            parts.append(f"{marker}{s.title}{status}{preview}")
        return "\n".join(parts)

    async def generate_section_content(
        self,
        db: AsyncSession,
        section_id: int,
        tender_requirements: Optional[str] = None,
        additional_context: Optional[str] = None,
    ) -> str:
        """为指定章节生成 AI 内容"""
        # 查询章节
        section_result = await db.execute(
            select(BidSection).where(BidSection.id == section_id, BidSection.is_deleted == 0)
        )
        section = section_result.scalar_one_or_none()
        if not section:
            raise Exception("章节不存在")

        # 查询标书项目标题
        project_result = await db.execute(
            select(BidProject).where(BidProject.id == section.project_id, BidProject.is_deleted == 0)
        )
        project = project_result.scalar_one_or_none()
        project_title = project.title if project else "未知项目"

        # 收集上下文
        company_info = await self._get_company_info(db)
        # 用户手动传入优先，否则从解析结果获取
        if tender_requirements:
            tender_req = f"【招标要求】\n{tender_requirements}"
        else:
            tender_req = await self._get_tender_requirements(db, section.project_id)
        sections_ctx = await self._get_other_sections_context(db, section.project_id, section_id)
        knowledge_ref = await self._get_knowledge_reference(db, section.title)
        scoring_block = await self._get_scoring_items_for_section(db, section_id)

        additional_part = f"\n额外要求：\n{additional_context}" if additional_context else ""
        knowledge_part = f"\n{knowledge_ref}" if knowledge_ref else ""
        scoring_part = f"\n{scoring_block}\n" if scoring_block else ""

        prompt = f"""你是一个专业的标书编写助手。请为以下标书章节撰写内容。

标书项目：{project_title}
当前章节：{section.title}
{scoring_part}
{sections_ctx}

{tender_req}

{company_info}
{knowledge_part}
{additional_part}

请撰写专业、详实的标书内容。要求：
1. 如有【关联评分项】，**逐条对照评分细则响应**（每条评分要素至少一段文字 + 引用一个企业素材作为佐证）
2. 内容要有针对性，紧扣招标要求
3. 引用具体的业绩案例（包含项目名称、甲方、金额、完成时间）和证书编号——数据要具体（不要"丰富经验"，要"承接 X 个同类项目"）
4. 如果知识库有相关参考模板，参考其结构和写法，但不要照搬
5. 语言正式规范，符合投标文件要求
6. 输出 markdown，含小标题（## 子节）和列表
7. 直接输出章节内容，不要加章节大标题（标题已有），不要带"以下是..."引导语"""

        client = self._get_client()
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个经验丰富的标书编写专家，擅长根据招标要求和企业资料撰写高质量的投标文件内容。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.7,
        )

        return response.choices[0].message.content.strip()

    async def generate_section_content_stream(
        self,
        db: AsyncSession,
        section_id: int,
        tender_requirements: Optional[str] = None,
        additional_context: Optional[str] = None,
    ):
        """流式生成章节内容，yield 每个文本片段"""
        section_result = await db.execute(
            select(BidSection).where(BidSection.id == section_id, BidSection.is_deleted == 0)
        )
        section = section_result.scalar_one_or_none()
        if not section:
            raise Exception("章节不存在")

        project_result = await db.execute(
            select(BidProject).where(BidProject.id == section.project_id, BidProject.is_deleted == 0)
        )
        project = project_result.scalar_one_or_none()
        project_title = project.title if project else "未知项目"

        company_info = await self._get_company_info(db)
        if tender_requirements:
            tender_req = f"【招标要求】\n{tender_requirements}"
        else:
            tender_req = await self._get_tender_requirements(db, section.project_id)
        sections_ctx = await self._get_other_sections_context(db, section.project_id, section_id)
        knowledge_ref = await self._get_knowledge_reference(db, section.title)
        additional_part = f"\n额外要求：\n{additional_context}" if additional_context else ""
        knowledge_part = f"\n{knowledge_ref}" if knowledge_ref else ""

        prompt = f"""你是一个专业的标书编写助手。请为以下标书章节撰写内容。

标书项目：{project_title}
当前章节：{section.title}

{sections_ctx}

{tender_req}

{company_info}
{knowledge_part}
{additional_part}

请撰写专业、详实的标书内容。要求：
1. 内容要有针对性，紧扣招标要求
2. 充分展示企业的资质和实力
3. 引用具体的业绩案例（包含项目名称、甲方、金额、完成时间）和证书编号
4. 如果知识库有相关参考模板，参考其结构和写法，但不要照搬
5. 语言正式规范，符合投标文件要求
6. 篇幅适中（500-2000字）
7. 直接输出章节内容，不要加标题（标题已有），不要加 markdown 标记"""

        client = self._get_client()
        stream = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个经验丰富的标书编写专家，擅长根据招标要求和企业资料撰写高质量的投标文件内容。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.7,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def check_bid_compliance(
        self,
        db: AsyncSession,
        project_id: int,
        tender_requirements: Optional[str] = None,
    ) -> dict:
        """废标检查 — AI 对照招标要求检查标书"""
        # 获取招标要求（用户传入优先）
        if tender_requirements:
            tender_req = f"【招标要求】\n{tender_requirements}"
        else:
            tender_req = await self._get_tender_requirements(db, project_id)
        if not tender_req:
            return {"status": "warning", "message": "未找到招标文件解析结果，无法进行废标检查", "items": []}

        # 获取所有章节内容
        result = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project_id, BidSection.is_deleted == 0
            ).order_by(BidSection.sort_order.asc())
        )
        sections = result.scalars().all()

        bid_content = "【当前标书内容】\n"
        for s in sections:
            bid_content += f"\n## {s.title}\n"
            bid_content += (s.content or "（未填写）") + "\n"

        prompt = f"""{tender_req}

{bid_content}

请作为废标检查专家，对照招标文件要求逐条检查当前标书，输出 JSON 格式（不要 ```json 包裹）：

{{
  "overall_status": "PASS 或 WARNING 或 FAIL",
  "score": 0到100的评分,
  "summary": "整体评价（一句话）",
  "items": [
    {{
      "category": "格式要求/资质文件/技术方案/商务报价/其他",
      "requirement": "招标文件的要求原文摘要",
      "status": "PASS/WARNING/FAIL",
      "detail": "检查结果说明",
      "suggestion": "改进建议（如果有）"
    }}
  ]
}}

重点检查：
1. 招标文件要求的章节是否都有
2. 资质要求是否满足
3. 评分项是否都有对应内容
4. 格式要求是否满足
5. 容易导致废标的关键条款"""

        client = self._get_client()
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个严谨的招投标废标检查专家，擅长发现标书中的问题和风险。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=8192,
            temperature=0.1,
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text
            if result_text.endswith("```"):
                result_text = result_text[:-3]

        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            return {"status": "error", "message": "AI 返回格式异常", "items": [], "raw": result_text[:500]}


bid_ai_service = BidAIService()
