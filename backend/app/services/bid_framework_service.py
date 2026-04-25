"""
标书框架自动生成服务
根据招标文件解析结果 + 标准模板，一键生成标书章节结构
"""

import asyncio
import json
import logging
import time
from typing import AsyncIterator, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import BidProject, BidSection
from app.models.knowledge import KnowledgeTemplate
from app.models.tender_document import TenderDocument

logger = logging.getLogger(__name__)

# 标准标书框架（政府采购·印刷服务类）
# 从多份真实投标文件总结，覆盖资格响应 + 商务报价 + 技术方案三大板块
# 每个章节有：标题、类型、知识库匹配关键词、说明
STANDARD_FRAMEWORK = [
    # ===== 一、资格响应部分 =====
    {
        "title": "响应函（磋商响应函）",
        "section_type": "TEMPLATE",
        "keywords": ["响应函", "磋商响应", "投标函"],
        "description": "格式文件，表明参与投标意愿和承诺",
    },
    {
        "title": "法定代表人身份证明书",
        "section_type": "TEMPLATE",
        "keywords": ["法定代表人", "身份证明"],
        "description": "法定代表人身份证明及身份证复印件",
    },
    {
        "title": "授权委托书",
        "section_type": "TEMPLATE",
        "keywords": ["授权委托", "授权书"],
        "description": "法定代表人授权委托书",
    },
    {
        "title": "无重大违法记录声明函",
        "section_type": "TEMPLATE",
        "keywords": ["违法记录", "声明函", "不良信用"],
        "description": "无违法记录和不良信用声明",
    },
    {
        "title": "中小企业声明函",
        "section_type": "TEMPLATE",
        "keywords": ["中小企业", "中小企业声明"],
        "description": "中小企业声明函（政采加分项，需符合工信部中小企业划型标准）",
    },
    {
        "title": "承诺函",
        "section_type": "TEMPLATE",
        "keywords": ["承诺函", "诚信履约"],
        "description": "诚信履约承诺、主要标的承诺等",
    },
    {
        "title": "企业资质证明",
        "section_type": "LIBRARY",
        "keywords": ["营业执照", "资质", "许可证"],
        "description": "营业执照、出版物印刷许可证、资质证书等扫描件",
    },
    {
        "title": "财务状况证明",
        "section_type": "LIBRARY",
        "keywords": ["财务", "审计报告", "纳税", "社保"],
        "description": "审计报告、纳税证明、社保缴纳证明",
    },
    {
        "title": "信用记录查询截图",
        "section_type": "MANUAL",
        "keywords": ["信用中国", "信用记录", "信用查询"],
        "description": "信用中国、中国政府采购网等信用记录查询截图（需手动截图上传）",
    },
    {
        "title": "业绩证明材料",
        "section_type": "LIBRARY",
        "keywords": ["业绩", "合同", "中标通知"],
        "description": "从企业资料库引用业绩案例及合同证明",
    },
    # ===== 二、商务报价部分 =====
    {
        "title": "响应报价表",
        "section_type": "MANUAL",
        "keywords": ["报价表", "报价一览"],
        "description": "报价一览表、分项报价（需手动填写金额）",
    },
    {
        "title": "商务条款偏离表",
        "section_type": "AI_GENERATE",
        "keywords": ["商务偏离", "商务响应", "商务条款"],
        "description": "商务条款响应/偏离表（AI根据招标要求和公司情况生成）",
    },
    {
        "title": "技术偏离表",
        "section_type": "AI_GENERATE",
        "keywords": ["技术偏离", "技术响应", "技术条款"],
        "description": "技术条款响应/偏离表（AI根据技术要求逐项响应）",
    },
    # ===== 三、技术方案部分 =====
    {
        "title": "整体服务方案",
        "section_type": "AI_GENERATE",
        "keywords": ["服务方案", "整体服务", "技术方案"],
        "description": "整体服务/技术方案（AI根据招标要求生成）",
    },
    {
        "title": "印刷工艺及色彩管理方案",
        "section_type": "AI_GENERATE",
        "keywords": ["印刷工艺", "色彩管理", "印刷技术", "工艺方案"],
        "description": "印刷工艺流程、色彩管理体系、打样校色流程",
    },
    {
        "title": "质量控制及保证措施",
        "section_type": "AI_GENERATE",
        "keywords": ["质量控制", "质量保证", "质量管理"],
        "description": "质量管理体系、检验标准、保证措施",
    },
    {
        "title": "项目实施进度计划",
        "section_type": "AI_GENERATE",
        "keywords": ["进度计划", "实施计划", "工期安排"],
        "description": "项目实施时间节点、进度安排、里程碑计划",
    },
    {
        "title": "包装运输配送方案",
        "section_type": "AI_GENERATE",
        "keywords": ["包装", "运输", "配送"],
        "description": "包装保护、运输方案、配送计划",
    },
    {
        "title": "保密措施",
        "section_type": "AI_GENERATE",
        "keywords": ["保密", "保密措施", "信息安全"],
        "description": "政府印刷品保密管理制度、人员保密协议、废品销毁流程",
    },
    {
        "title": "绿色印刷及环保措施",
        "section_type": "AI_GENERATE",
        "keywords": ["绿色印刷", "环保", "节能", "绿色"],
        "description": "绿色印刷认证、环保材料使用、VOCs排放控制、废料回收",
    },
    {
        "title": "安全生产方案",
        "section_type": "AI_GENERATE",
        "keywords": ["安全生产", "安全管理", "安全措施"],
        "description": "安全生产管理制度、应急预案、安全培训",
    },
    {
        "title": "售后服务方案",
        "section_type": "AI_GENERATE",
        "keywords": ["售后服务"],
        "description": "售后服务体系、响应机制、保修承诺",
    },
    {
        "title": "人员配备",
        "section_type": "LIBRARY",
        "keywords": ["人员配备", "团队", "项目组"],
        "description": "项目团队人员清单及证书",
    },
    {
        "title": "设备配备",
        "section_type": "LIBRARY",
        "keywords": ["设备配备", "设备", "机器"],
        "description": "投入设备清单及证明（印刷机、装订机、CTP等）",
    },
    {
        "title": "服务承诺",
        "section_type": "TEMPLATE",
        "keywords": ["服务承诺"],
        "description": "服务承诺函",
    },
]


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


class BidFrameworkService:

    async def generate_framework(
        self,
        db: AsyncSession,
        project_id: int,
        user_id: int,
        custom_chapters: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        一键生成标书框架

        优先使用招标文件解析出的章节要求，否则用标准模板。
        对每个章节自动分配类型并匹配知识库模板。
        """
        # 查项目
        project_result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise Exception("标书项目不存在")

        # 如果传入了自定义章节（来自招标文件解析），和标准框架合并
        if custom_chapters:
            framework = self._merge_with_standard(custom_chapters)
        else:
            framework = STANDARD_FRAMEWORK.copy()

        # 为每个章节匹配知识库模板
        created_sections = []
        for i, chapter in enumerate(framework):
            template_id = await self._match_template(db, chapter.get("keywords", []))
            content = ""

            # TEMPLATE 类型：自动从知识库填充内容
            if chapter["section_type"] == "TEMPLATE" and template_id:
                content = await self._fill_template(db, template_id, project)

            section = BidSection(
                project_id=project_id,
                title=chapter["title"],
                content=content,
                sort_order=i + 1,
                section_type=chapter["section_type"],
                template_id=template_id,
                status="COMPLETED" if content else "PENDING",
                word_count=len(content) if content else 0,
                created_by=user_id,
                updated_by=user_id,
            )
            db.add(section)
            await db.flush()
            await db.refresh(section)

            created_sections.append({
                "id": section.id,
                "title": section.title,
                "section_type": section.section_type,
                "template_id": section.template_id,
                "has_content": bool(content),
                "word_count": section.word_count,
            })

        return created_sections

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
          - extract_failed: {message, duration_ms}（降级，仍继续创建空章节）
          - section_created: {title, section_type, has_content}
          - done: {total, with_content}
          - error: {message}
        """
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
        existing = await db.execute(
            select(BidSection).where(BidSection.project_id == project_id, BidSection.is_deleted == 0).limit(1)
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
            parse_result = json.loads(td.parse_result) if isinstance(td.parse_result, str) else td.parse_result
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
            extract_result = await asyncio.to_thread(
                tender_ai_parser.extract_chapter_templates, td.raw_text, chapter_titles
            )
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

    def _merge_with_standard(self, custom_chapters: List[str]) -> List[dict]:
        """将招标文件要求的章节与标准框架合并"""
        result = []
        used_standards = set()

        for chapter_title in custom_chapters:
            # 尝试匹配标准框架
            matched = False
            for std in STANDARD_FRAMEWORK:
                if any(kw in chapter_title for kw in std.get("keywords", [])) or \
                   std["title"] in chapter_title or chapter_title in std["title"]:
                    result.append({**std, "title": chapter_title})
                    used_standards.add(std["title"])
                    matched = True
                    break

            if not matched:
                # 未匹配到标准框架，根据关键词推断类型
                section_type = self._infer_type(chapter_title)
                result.append({
                    "title": chapter_title,
                    "section_type": section_type,
                    "keywords": [chapter_title],
                    "description": "",
                })

        # 补充标准框架中未被覆盖的必要章节
        essential = ["无重大违法记录声明函", "响应报价表", "法定代表人身份证明书", "中小企业声明函"]
        for std in STANDARD_FRAMEWORK:
            if std["title"] in essential and std["title"] not in used_standards:
                # 检查是否已有类似章节
                has_similar = any(
                    any(kw in r["title"] for kw in std.get("keywords", []))
                    for r in result
                )
                if not has_similar:
                    result.append(std)

        return result

    def _infer_type(self, title: str) -> str:
        """根据章节标题推断类型"""
        template_keywords = ["函", "声明", "承诺", "授权", "委托", "身份证明"]
        library_keywords = ["营业执照", "资质", "业绩", "证书", "人员", "设备", "财务", "审计", "纳税", "社保"]
        manual_keywords = ["报价", "价格", "费率", "截图", "信用记录"]

        for kw in template_keywords:
            if kw in title:
                return "TEMPLATE"
        for kw in library_keywords:
            if kw in title:
                return "LIBRARY"
        for kw in manual_keywords:
            if kw in title:
                return "MANUAL"
        return "AI_GENERATE"

    async def _match_template(self, db: AsyncSession, keywords: List[str]) -> Optional[int]:
        """从知识库匹配最相关的模板（按关键词命中数排序，命中越多越精准）"""
        if not keywords:
            return None

        from sqlalchemy import or_
        conditions = []
        for kw in keywords[:3]:
            conditions.append(KnowledgeTemplate.title.contains(kw))
            conditions.append(KnowledgeTemplate.tags.contains(kw))

        if not conditions:
            return None

        result = await db.execute(
            select(KnowledgeTemplate)
            .where(KnowledgeTemplate.is_deleted == 0, or_(*conditions))
        )
        candidates = result.scalars().all()
        if not candidates:
            return None

        # 按关键词命中数排序，命中数相同时按 usage_count 排序
        def match_score(tmpl):
            score = 0
            text = (tmpl.title or "") + " " + (tmpl.tags or "")
            for kw in keywords:
                if kw in text:
                    score += 1
            return (score, tmpl.usage_count or 0)

        best = max(candidates, key=match_score)
        best.usage_count = (best.usage_count or 0) + 1
        await db.flush()
        return best.id

    async def _fill_template(self, db: AsyncSession, template_id: int, project: BidProject) -> str:
        """将模板中的旧项目信息替换为当前项目信息（纯文本替换，不调 AI）"""
        import re

        result = await db.execute(
            select(KnowledgeTemplate).where(KnowledgeTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template or not template.content:
            return ""

        content = template.content

        # 获取当前招标信息
        project_name = project.title or ""
        tender_no = ""
        tender_unit = ""
        if project.tender_id:
            from app.models.tender import Tender
            tender_result = await db.execute(select(Tender).where(Tender.id == project.tender_id))
            tender = tender_result.scalar_one_or_none()
            if tender:
                project_name = tender.title or project.title
                tender_no = tender.tender_no or ""
                tender_unit = tender.tender_unit or ""

        from datetime import datetime
        today = datetime.now()

        # 替换已知的旧项目信息（来自安徽博物院投标文件模板）
        old_replacements = [
            # 项目名称
            ("安徽博物院（安徽省文物鉴定站）年度印刷服务", project_name),
            ("安徽博物院（安徽省文物鉴定站）", tender_unit or project_name),
            # 项目编号
            ("25AT134026809637", tender_no),
            # 代理机构
            ("安徽安天利信工程管理股份有限公司", tender_unit),
        ]

        for old, new in old_replacements:
            if new:
                content = content.replace(old, new)

        # 替换签章处的日期（仅限"日期"/"日 期"标签后的日期，不替换正文中的固定日期）
        content = re.sub(
            r'(日\s*期[：:]\s*)\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日',
            lambda m: f'{m.group(1)}{today.strftime("%Y年%m月%d日")}',
            content
        )

        # 替换占位符格式
        from app.config import settings
        replacements = {
            "{项目名称}": project_name,
            "{公司名称}": settings.COMPANY_NAME,
            "{公司地址}": settings.COMPANY_ADDRESS,
            "{公司电话}": settings.COMPANY_PHONE,
            "{公司传真}": settings.COMPANY_FAX,
            "{公司邮编}": settings.COMPANY_ZIPCODE,
            "{法定代表人}": settings.COMPANY_LEGAL_PERSON,
            "{统一社会信用代码}": settings.COMPANY_CREDIT_CODE,
            "{开户银行}": settings.COMPANY_BANK,
            "{银行账号}": settings.COMPANY_BANK_ACCOUNT,
            "{日期}": today.strftime("%Y年%m月%d日"),
            "{年}": str(today.year),
            "{月}": str(today.month),
            "{日}": str(today.day),
            "{招标编号}": tender_no,
            "{招标单位}": tender_unit,
        }
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        # 清理 PDF 提取导致的日期换行问题
        # "授权委托日期：\n2026\n年\n04\n月\n13\n日" → "授权委托日期：2026年04月13日"
        content = re.sub(
            r'(日期[：:]\s*)\n*(\d{4})\n*年\n*(\d{1,2})\n*月\n*(\d{1,2})\n*日',
            lambda m: f'{m.group(1)}{m.group(2)}年{m.group(3)}月{m.group(4)}日',
            content
        )

        # 清理连续空行（超过2个换行合并为2个）
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content


bid_framework_service = BidFrameworkService()
