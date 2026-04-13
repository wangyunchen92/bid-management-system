"""
标书框架自动生成服务
根据招标文件解析结果 + 标准模板，一键生成标书章节结构
"""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import BidProject, BidSection
from app.models.knowledge import KnowledgeTemplate
from app.models.tender_document import TenderDocument

logger = logging.getLogger(__name__)

# 标准标书框架（从3份真实投标文件总结）
# 每个章节有：标题、类型、知识库匹配关键词、说明
STANDARD_FRAMEWORK = [
    {
        "title": "响应函（磋商响应函）",
        "section_type": "TEMPLATE",
        "keywords": ["响应函", "磋商响应"],
        "description": "格式文件，表明参与投标意愿和承诺",
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
        "title": "承诺函",
        "section_type": "TEMPLATE",
        "keywords": ["承诺函", "诚信履约"],
        "description": "诚信履约承诺、主要标的承诺等",
    },
    {
        "title": "响应报价表",
        "section_type": "MANUAL",
        "keywords": [],
        "description": "报价一览表、分项报价（需手动填写金额）",
    },
    {
        "title": "商务条款偏离表",
        "section_type": "TEMPLATE",
        "keywords": ["商务偏离", "商务响应"],
        "description": "商务条款响应/偏离表",
    },
    {
        "title": "业绩证明材料",
        "section_type": "LIBRARY",
        "keywords": ["业绩"],
        "description": "从企业资料库引用业绩案例及合同证明",
    },
    {
        "title": "企业资质证明",
        "section_type": "LIBRARY",
        "keywords": ["营业执照", "资质"],
        "description": "营业执照、资质证书、许可证等扫描件",
    },
    {
        "title": "整体服务方案",
        "section_type": "AI_GENERATE",
        "keywords": ["服务方案", "整体服务"],
        "description": "核心技术/服务方案（AI根据招标要求生成）",
    },
    {
        "title": "质量控制及保证措施",
        "section_type": "AI_GENERATE",
        "keywords": ["质量控制", "质量保证"],
        "description": "质量管理体系、检验标准、保证措施",
    },
    {
        "title": "包装运输配送方案",
        "section_type": "AI_GENERATE",
        "keywords": ["包装", "运输", "配送"],
        "description": "包装保护、运输方案、配送计划",
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
        "keywords": ["人员配备", "团队"],
        "description": "项目团队人员清单及证书",
    },
    {
        "title": "设备配备",
        "section_type": "LIBRARY",
        "keywords": ["设备配备", "设备"],
        "description": "投入设备清单及证明",
    },
    {
        "title": "服务承诺",
        "section_type": "TEMPLATE",
        "keywords": ["服务承诺"],
        "description": "服务承诺函",
    },
]


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

        # 补充标准框架中未被覆盖的必要章节（声明函等）
        essential = ["无重大违法记录声明函", "响应报价表"]
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
        template_keywords = ["函", "声明", "承诺", "授权", "委托", "偏离表"]
        library_keywords = ["营业执照", "资质", "业绩", "证书", "人员", "设备"]
        manual_keywords = ["报价", "价格", "费率"]

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
        """从知识库匹配最相关的模板"""
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
            .order_by(KnowledgeTemplate.usage_count.desc())
            .limit(1)
        )
        template = result.scalar_one_or_none()
        if template:
            # 增加使用次数
            template.usage_count = (template.usage_count or 0) + 1
            await db.flush()
            return template.id
        return None

    async def _fill_template(self, db: AsyncSession, template_id: int, project: BidProject) -> str:
        """从知识库模板填充内容，替换占位符"""
        result = await db.execute(
            select(KnowledgeTemplate).where(KnowledgeTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template or not template.content:
            return ""

        content = template.content

        # 替换常见占位符
        from datetime import datetime
        today = datetime.now()

        replacements = {
            "{项目名称}": project.title or "",
            "{公司名称}": "合肥新安彩印包装有限公司",  # TODO: 从系统配置或企业信息获取
            "{日期}": today.strftime("%Y年%m月%d日"),
            "{年}": str(today.year),
            "{月}": str(today.month),
            "{日}": str(today.day),
        }

        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        return content


bid_framework_service = BidFrameworkService()
