"""
标书框架自动生成服务
根据招标文件解析结果 + 标准模板，一键生成标书章节结构
"""

import json
import logging
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
                content = await self._fill_template(db, template_id, project, chapter["section_type"])

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

        模板原文已经在招标文件解析阶段（tender_ai_parser.parse）一并抽取，
        此方法直接读取 parse_result 中的结构化 chapters，不再重复调 AI。

        事件类型：
          - section_created: {title, section_type, has_content}
          - done: {total, with_content}
          - error: {message}
        """
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
        if not td.parse_result:
            yield {"type": "error", "message": "招标文件未解析完成（缺少解析结果）"}
            return

        try:
            parse_result = json.loads(td.parse_result) if isinstance(td.parse_result, str) else td.parse_result
        except Exception:
            yield {"type": "error", "message": "招标文件解析结果格式异常"}
            return

        chapters_raw = (parse_result.get("bid_document_requirements") or {}).get("chapters") or []
        if not chapters_raw:
            yield {"type": "error", "message": "招标文件未识别到章节列表"}
            return

        # 4. 归一化章节格式（兼容旧版只有标题字符串、新版结构化对象）
        ai_chapters = []
        for c in chapters_raw:
            if isinstance(c, str):
                ai_chapters.append({
                    "title": c,
                    "section_type": self._infer_type(c),
                    "template": "",
                    "matched": False,
                })
            elif isinstance(c, dict) and c.get("title"):
                ai_chapters.append({
                    "title": c["title"],
                    "section_type": c.get("section_type") or self._infer_type(c["title"]),
                    "template": c.get("template") or "",
                    "matched": bool(c.get("matched")),
                })

        if not ai_chapters:
            yield {"type": "error", "message": "招标文件章节格式异常"}
            return

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
                    content = await self._fill_template(db, template_id, project, section_type)
            elif content:
                # AI 抽出的模板也走占位符替换（中文括号填空、签章日期、{公司名称}等）
                content = await self._apply_substitutions(db, content, project, section_type)

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

    async def _fill_template(self, db: AsyncSession, template_id: int, project: BidProject, section_type: str = "TEMPLATE") -> str:
        """从知识库加载模板并填充当前项目信息"""
        result = await db.execute(
            select(KnowledgeTemplate).where(KnowledgeTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template or not template.content:
            return ""
        return await self._apply_substitutions(db, template.content, project, section_type)

    async def _apply_substitutions(self, db: AsyncSession, content: str, project: BidProject, section_type: str = None) -> str:
        """对任意模板文本做占位符替换（旧项目文本/花括号占位/中文括号填空/markdown 空格填充/签章日期）"""
        import re
        from datetime import datetime
        from app.config import settings

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

        today = datetime.now()
        company_name = settings.COMPANY_NAME

        # 1. 替换已知的旧项目信息（来自安徽博物院投标文件模板）
        old_replacements = [
            ("安徽博物院（安徽省文物鉴定站）年度印刷服务", project_name),
            ("安徽博物院（安徽省文物鉴定站）", tender_unit or project_name),
            ("25AT134026809637", tender_no),
            ("安徽安天利信工程管理股份有限公司", tender_unit),
        ]
        for old, new in old_replacements:
            if new:
                content = content.replace(old, new)

        # 2. 替换签章处的日期
        content = re.sub(
            r'(日\s*期[：:]\s*)\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日',
            lambda m: f'{m.group(1)}{today.strftime("%Y年%m月%d日")}',
            content
        )

        # 3. 花括号占位符
        replacements = {
            "{项目名称}": project_name,
            "{公司名称}": company_name,
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

        # 4. 招标文件原生的中文括号填空：「           （供应商名称）」→「合肥新安彩印（供应商名称）」
        # 匹配空白/全角空白/下划线 + 中文括号标签
        bracket_fills = [
            (r"(供应商名称|公司名称|投标人名称|响应人名称|磋商供应商名称)", company_name),
            (r"(供应商授权代表姓名|授权代表姓名|授权委托人姓名|被授权人姓名)", settings.COMPANY_LEGAL_PERSON),
            (r"(法定代表人姓名|法人代表姓名)", settings.COMPANY_LEGAL_PERSON),
            (r"(请填写手机号码|联系电话|联系方式|供应商联系电话)", settings.COMPANY_PHONE),
            (r"(供应商地址|公司地址|注册地址|通讯地址)", settings.COMPANY_ADDRESS),
            (r"(统一社会信用代码|信用代码|社会信用代码)", settings.COMPANY_CREDIT_CODE),
        ]
        for label_pattern, value in bracket_fills:
            if not value:
                continue
            content = re.sub(
                rf"[ 　_]{{2,}}（({label_pattern})）",
                lambda m, v=value: f"{v}（{m.group(1)}）",
                content
            )

        # 5. markdown 表格空白单元格填充：「| 供应商名称 |  |」→「| 供应商名称 | 合肥新安彩印 |」
        cell_fills = [
            (r"供应商名称|公司名称|投标人名称|响应人名称", company_name),
            (r"法定代表人|法人代表", settings.COMPANY_LEGAL_PERSON),
            (r"联系电话|电话|联系方式", settings.COMPANY_PHONE),
            (r"公司地址|注册地址|通讯地址|地址", settings.COMPANY_ADDRESS),
            (r"统一社会信用代码|信用代码|社会信用代码", settings.COMPANY_CREDIT_CODE),
            (r"开户银行", settings.COMPANY_BANK),
            (r"银行账号|账号", settings.COMPANY_BANK_ACCOUNT),
            (r"传真", settings.COMPANY_FAX),
            (r"邮编|邮政编码", settings.COMPANY_ZIPCODE),
        ]
        for label_pattern, value in cell_fills:
            if not value:
                continue
            content = re.sub(
                rf"(\|\s*({label_pattern})\s*\|)\s*\|",
                lambda m, v=value: f"{m.group(1)} {v} |",
                content
            )

        # 6. 清理 PDF 提取导致的日期换行问题
        content = re.sub(
            r'(日期[：:]\s*)\n*(\d{4})\n*年\n*(\d{1,2})\n*月\n*(\d{1,2})\n*日',
            lambda m: f'{m.group(1)}{m.group(2)}年{m.group(3)}月{m.group(4)}日',
            content
        )

        # 7. 表格上下补空行（避免 markdown 解析器把表格上下文吃进表格）
        # 7a. 表格行「| ... |」后紧跟非空非|行 → 插空行
        content = re.sub(r'(^\|[^\n]*\|)\n(?!\n|\|)', r'\1\n\n', content, flags=re.MULTILINE)
        # 7b. 非空非|行紧跟「| ... |」首行 → 插空行
        content = re.sub(r'(^[^|\n][^\n]*)\n(\|[^\n]*\|)', r'\1\n\n\2', content, flags=re.MULTILINE)

        # 8. 标书填空规范化（空单元格、签章块、段落分隔）
        content = self._format_template(content, section_type)

        # 9. 资料库自动填入（身份证扫描件、营业执照等）
        content = await self._fill_from_library(db, content)

        # 10. 清理连续空行
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content

    async def _fill_from_library(self, db: AsyncSession, content: str) -> str:
        """从企业资料库自动注入附件标记。
        - 「身份证扫描件」cell/独立行 → 法人身份证（lib_personnel_cert，cert_type=身份证明）
        - 「营业执照」cell/独立行 → lib_qualification 同名记录
        - 命中且有 file_path → 替换为 [附件:path:filename]
        - 命中但无文件 → 替换为 ____（请到企业资料库上传 XXX）
        """
        import re
        from app.config import settings
        from app.models.library import PersonnelCert, Qualification

        async def _lookup_personnel(cert_types: list[str], person_name: str = None):
            cond = [PersonnelCert.is_deleted == 0, PersonnelCert.cert_type.in_(cert_types)]
            if person_name:
                cond.append(PersonnelCert.person_name == person_name)
            r = await db.execute(select(PersonnelCert).where(*cond).limit(1))
            return r.scalar_one_or_none()

        async def _lookup_qualification(cert_names: list[str]):
            r = await db.execute(
                select(Qualification).where(
                    Qualification.is_deleted == 0,
                    Qualification.cert_name.in_(cert_names),
                ).limit(1)
            )
            return r.scalar_one_or_none()

        def _to_marker(record, fallback_label: str) -> str:
            """有 file_path → 附件标记；无 file_path → 提示填写"""
            if record and getattr(record, "file_path", None):
                fp = record.file_path
                fname = fp.split("/")[-1]
                return f"[附件:{fp}:{fname}]"
            return f"____（请到企业资料库上传：{fallback_label}）"

        # 身份证扫描件
        id_cert = await _lookup_personnel(["身份证明", "身份证"], settings.COMPANY_LEGAL_PERSON)
        if not id_cert:
            id_cert = await _lookup_personnel(["身份证明", "身份证"])
        id_marker = _to_marker(id_cert, f"{settings.COMPANY_LEGAL_PERSON}身份证扫描件")
        # 表格 cell 用 lookahead 兼容连续相邻 cell（| 身份证扫描件 | 身份证扫描件 |）
        content = re.sub(r'(\|\s*)身份证扫描件(\s*)(?=\|)', rf'\1{id_marker}\2', content)
        # 独立行
        content = re.sub(r'^身份证扫描件\s*$', id_marker, content, flags=re.MULTILINE)

        # 营业执照（含「营业执照扫描件」「营业执照副本」等）
        biz = await _lookup_qualification(["营业执照", "营业执照副本"])
        biz_marker = _to_marker(biz, "营业执照扫描件")
        content = re.sub(r'(\|\s*)营业执照(扫描件|副本)?(\s*)(?=\|)', rf'\1{biz_marker}\3', content)

        return content

    def _format_template(self, content: str, section_type: str = None) -> str:
        """标书模板格式规范化：
        - 空 markdown 单元格 → ____
        - "xxx：" 后大量空格 → ____ （日期类自动给出 ____年__月__日 格式）
        - TEMPLATE/MANUAL 类章节末尾若无签章块 → 自动追加（插入到 注：之前）
        - 连续编号行（1./2./(1)/（1）)之间补空行 → 让 markdown 渲染独立段落
        """
        import re

        lines = content.split('\n')

        # 8a. 表格行规整：补齐缺失的尾部 |、按分隔符行的列数对齐
        new_lines = []
        in_table = False
        col_count = 0
        for line in lines:
            stripped = line.rstrip()
            if stripped.startswith('|'):
                # 分隔符行（| --- | --- |）
                if re.match(r'^\|[\s\-:|]+\|\s*$', stripped):
                    col_count = stripped.count('|') - 1
                    in_table = True
                    new_lines.append(stripped)
                    continue
                # 数据行
                # 补齐结尾 |
                if not stripped.endswith('|'):
                    stripped = stripped.rstrip() + ' |'
                # 按列数补齐空单元
                if in_table and col_count > 0:
                    parts = stripped.split('|')
                    while len(parts) < col_count + 2:
                        parts.insert(-1, ' ')
                    stripped = '|'.join(parts)
                new_lines.append(stripped)
            else:
                in_table = False
                new_lines.append(line)
        content = '\n'.join(new_lines)

        # 8a-2. 空 markdown 单元格填 ____
        new_lines = []
        for line in content.split('\n'):
            if line.startswith('|') and not re.match(r'^\|[\s\-:|]+\|$', line):
                parts = line.split('|')
                for i in range(1, len(parts) - 1):
                    if parts[i].strip() == '':
                        parts[i] = ' ____ '
                line = '|'.join(parts)
            new_lines.append(line)
        content = '\n'.join(new_lines)

        # 8b. "xxx：" 后大量空白 → 日期类自动填今天，其他类填 ____
        from datetime import datetime
        today_str = datetime.now().strftime("%Y年%m月%d日")
        # 日期类（日期/日 期/落款日期/签章日期/出具日期 等）
        content = re.sub(
            r'(日[ 　]*期[：:])[ 　]{3,}(?=$|\n)',
            rf'\1{today_str}',
            content,
            flags=re.MULTILINE,
        )
        # 占位符 ____年__月__日 也填实际日期
        content = re.sub(r'____年__月__日', today_str, content)
        # 其他文本类（签章/姓名/电话等）
        content = re.sub(
            r'([一-鿿]+[：:])[ 　]{3,}(?=$|\n)',
            r'\1____',
            content,
            flags=re.MULTILINE,
        )

        # 8c. TEMPLATE/MANUAL 末尾补签章块（如果缺）
        if section_type in ('TEMPLATE', 'MANUAL'):
            has_sign = bool(
                re.search(r'(供应商|供方|投标人).{0,4}[（(]?(电子)?(签章|盖章)[）)]?', content)
                or re.search(r'(签字|签名)[：:]', content)
            )
            if not has_sign:
                sign_block = f"\n\n供应商电子签章：____\n\n日　　　期：{today_str}\n"
                # 优先插在「注：」前面，否则追加末尾
                m = re.search(r'\n注[：:\s　]', content)
                if m:
                    content = content[:m.start()] + sign_block + content[m.start():]
                else:
                    content = content.rstrip() + sign_block

        # 8d. 连续段落行之间补空行（让 markdown 渲染独立段落）
        # 排除：表格行、列表项、已有空行
        lines = content.split('\n')
        out = []
        for i, line in enumerate(lines):
            out.append(line)
            if i + 1 >= len(lines):
                continue
            cur, nxt = line.strip(), lines[i + 1].strip()
            if not cur or not nxt:
                continue
            if cur.startswith('|') or nxt.startswith('|'):
                continue
            # 已经是 markdown 列表/标题就别动
            if re.match(r'^([-*+]|#{1,6}|\d+\.\s)', cur):
                continue
            if re.match(r'^([-*+]|#{1,6}|\d+\.\s)', nxt):
                continue
            out.append('')  # 插空行
        content = '\n'.join(out)

        return content


bid_framework_service = BidFrameworkService()
