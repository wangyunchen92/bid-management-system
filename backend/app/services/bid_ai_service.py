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
        """获取企业资料库摘要，作为 AI 上下文。

        策略：业绩按完成时间倒序最多 30 条；资质/人员/设备按 id 全部拉（一般 < 50 条）。
        AI 看到完整素材才能从中挑选最相关的引用。
        """
        parts = []

        # 资质证书（全部拿，按 id）
        result = await db.execute(
            select(Qualification).where(Qualification.is_deleted == 0)
            .order_by(Qualification.id).limit(50)
        )
        quals = result.scalars().all()
        if quals:
            parts.append(f"【企业资质】（共 {len(quals)} 条）")
            for q in quals:
                parts.append(f"- {q.cert_name}（{q.cert_type or ''}，编号：{q.cert_no or ''}）")

        # 业绩案例：按完成时间倒序（NULL 排在最后），最多 30 条
        from sqlalchemy import case as sa_case
        result = await db.execute(
            select(Achievement).where(Achievement.is_deleted == 0)
            .order_by(
                sa_case((Achievement.completion_date.is_(None), 1), else_=0),
                Achievement.completion_date.desc(),
                Achievement.id.desc(),
            )
            .limit(30)
        )
        achvs = result.scalars().all()
        if achvs:
            parts.append(f"\n【业绩案例】（共 {len(achvs)} 条，按完成时间倒序）")
            for a in achvs:
                amount = f"，合同金额{float(a.contract_amount)}万元" if a.contract_amount else ""
                date = f"，完成时间{a.completion_date.strftime('%Y年%m月') if a.completion_date else ''}" if a.completion_date else ""
                desc = f"，项目内容：{a.description}" if a.description else ""
                has_proof = "，有合同证明材料" if a.file_path else ""
                parts.append(f"- {a.project_name}（甲方：{a.client_name or ''}{amount}{date}{desc}{has_proof}）")

        # 人员证书
        result = await db.execute(
            select(PersonnelCert).where(PersonnelCert.is_deleted == 0)
            .order_by(PersonnelCert.id).limit(50)
        )
        certs = result.scalars().all()
        if certs:
            parts.append(f"\n【人员证书】（共 {len(certs)} 条）")
            for c in certs:
                parts.append(f"- {c.person_name}：{c.cert_name}（{c.cert_no or ''}）")

        # 产品/设备
        result = await db.execute(
            select(Product).where(Product.is_deleted == 0)
            .order_by(Product.id).limit(30)
        )
        prods = result.scalars().all()
        if prods:
            parts.append(f"\n【产品/设备】（共 {len(prods)} 条）")
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

    # 章节标题 → 库匹配关键词（长词拆短词，提高 tags 命中率）
    # 顺序敏感：长/具体的关键词靠前，避免"服务方案"先吃掉"售后服务方案"
    SECTION_TITLE_KEYWORDS = [
        (("售后服务",),                                ["售后服务"]),
        (("应急预案", "紧急订单"),                       ["应急预案", "应急响应"]),
        (("安全生产", "安全方案", "安全管理", "安全措施"), ["安全生产", "安全管理", "消防"]),
        (("印刷工艺", "色彩管理", "工艺方案"),            ["印刷工艺", "色彩管理", "打样"]),
        (("质量控制", "质量保证", "质量管理"),            ["质量控制", "质量管理"]),
        (("项目实施", "进度计划", "实施计划"),            ["进度计划", "实施计划"]),
        (("包装运输", "包装", "运输", "配送"),            ["包装", "运输", "配送"]),
        (("保密措施", "保密管理"),                       ["保密"]),
        (("绿色印刷", "环保", "节能"),                   ["绿色印刷", "环保", "节能"]),
        (("人员配备", "项目团队"),                      ["人员配备", "团队"]),
        (("设备配备", "投入设备"),                      ["设备配备"]),
        (("整体服务方案", "服务方案", "服务承诺"),         ["服务方案", "整体服务", "服务承诺"]),
    ]

    # 章节标题 → 必写子主题清单（让 AI 不能偷懒，逐项展开）
    # 顺序敏感：长/具体的 key 在前（避免 "服务方案" 先吃掉 "售后服务方案"）
    SECTION_CHECKLIST = {
        "售后服务": [
            "一、售后响应机制（响应时限分级 + 现场到达时限：合肥市内 ≤4 小时 / 安徽省内 ≤12 小时）",
            "二、问题处置流程（识别 + 评估 + 整改 + 验收 4 步，每步含责任人和时限）",
            "三、定期回访机制（频次 + 内容 + 满意度评估）",
            "四、应急绿色通道（紧急订单优先级 + 设备资源调配）",
            "五、违约责任与补偿承诺（不可抗力书面通知 + 时延补偿方案）",
        ],
        "应急预案": [
            "一、应急组织架构（应急小组 + 各成员职责 + 联系方式）",
            "二、紧急订单应急（识别 + 优先级排序 + 资源调配 + 加急生产 + 加急配送）",
            "三、错印重印应急（错误识别 + 资源优先调配 + 重印过程管控 + 快速交付）",
            "四、质量问题应急（现场处置 + 批量隔离 + 客户沟通 + 补偿方案）",
            "五、设备故障应急（备用设备启用 + 第三方合作方 + 切换流程 + 时限承诺）",
            "六、不可抗力应急（自然灾害 / 疫情 / 物流中断 等场景的备用方案）",
        ],
        "安全生产": [
            "一、安全生产组织管理（消防安全责任制 + 各级岗位职责 + 安全培训计划）",
            "二、车间安全操作规程（按设备分类：印刷机 / 裁切机 / 装订机 / 制版机 各项操作规程）",
            "三、用电与用火管理（消防器材配置 + 灭火器型号数量 + 巡检频次）",
            "四、应急预案（火灾 / 设备故障 / 人员伤害 三类场景，每类含响应时限 + 处置流程 + 责任人）",
            "五、安全检查与考核（每日/每周/每季 三级检查 + 隐患整改时限 + 奖惩措施）",
        ],
        "印刷工艺": [
            "一、专业校色设备配置（设备型号 + 校准周期 + 数据记录）",
            "二、印前工艺（设计排版 + 制版精度 + 出片定位 误差≤1mm）",
            "三、印中工艺（套印精度 ≤0.2mm + 油墨色谱 BL100% 等 + 网点 5%）",
            "四、印后工艺（覆膜 / 烫银 / 模切 / 锁线刷胶 等专项工艺标准）",
            "五、特殊工艺能力（按本项目品类列出对应工艺，如档案袋的高强度粘胶、学籍表的复写功能等）",
        ],
        "质量控制": [
            "一、质量管理体系（认证证书 + 体系覆盖范围）",
            "二、原料质量控制（纸张/油墨/辅料 入库检测 + 抽样标准）",
            "三、生产过程质量控制（首件 + 巡检 + 末件 三检制；关键工艺指标量化）",
            "四、成品质量验收（抽检比例 + 验收标准 + 合格率承诺）",
            "五、质量问题处置（投诉响应 + 整改 + 重印 + 补偿）",
        ],
        "包装运输": [
            "一、包装方案（外包装结构 + 防潮防水措施 + 标识规范）",
            "二、仓储管理（环境温湿度 + 卡板堆放 + 分区管理）",
            "三、配送方案（运输车辆 + 配送时效 + 跟踪签收）",
            "四、紧急配送应急方案",
        ],
        "保密措施": [
            "一、保密责任划分（项目负责人 + 各岗位人员 + 第三方）",
            "二、保密协议（员工保密协议 + 客户保密承诺）",
            "三、生产环节保密流程（设计 / 印刷 / 装订 / 配送 各环节）",
            "四、数据与废料管控（数字化加密 + 边角料销毁）",
            "五、应急泄密响应",
        ],
        "服务方案": [
            "一、项目理解与服务原则（针对本项目特点的理解 + 我方服务核心原则 + 总体目标）",
            "二、工艺执行能力（按本项目品类至少细分 3 种工艺标准：例 档案袋/学籍表/成绩单/封皮 等，每种含纸张克重、网点精度、墨层厚度、套印误差、装订工艺、抗拉强度等量化指标）",
            "三、质量管控体系（含 4 个子流程：日常监督 + 周期考核 + 缺陷整改 + 重印应急；每子流程含责任部门/触发条件/时限/验收标准）",
            "四、进度计划（含生产排程表：阶段/工期/责任人；以及关键里程碑：样品确认/批量开工/中期检查/交付验收 各时间节点）",
            "五、应急预案（至少 3 个场景：① 紧急订单加急生产 ② 错印重印资源调配 ③ 质量异议现场处置；每场景含识别→响应→处置→验收 4 步）",
            "六、保密管理机制（覆盖 3 维度：① 人员保密协议 + 岗位责任 ② 生产环境监控 ③ 数据/废料管控）",
            "七、服务响应与售后（含样品时限、交付频次、回访机制、售后免费补印承诺、问题处置时限）",
            "八、人员保障（项目经理职责 + 各环节对接人 + 替补/稳定性机制）",
            "九、设备保障（主用设备清单 + 备用设备储备 + 第三方应急合作方）",
            "十、数字化与创新（订单管理系统 + 加密存储 + 绿色印刷 等差异化亮点）",
        ],
    }

    def _section_title_to_checklist(self, title: str) -> list[str]:
        """根据章节标题返回必写子主题清单（让 AI 不能偷懒，按子主题展开）"""
        title = (title or "").strip()
        # 章节标题按关键词命中 checklist
        for key, items in self.SECTION_CHECKLIST.items():
            if key in title or any(kw in title for kw in key.split("/")):
                return items
        # 兜底：按 SECTION_TITLE_KEYWORDS 第一个 trigger 命中 checklist
        for triggers, _ in self.SECTION_TITLE_KEYWORDS:
            for t in triggers:
                for key, items in self.SECTION_CHECKLIST.items():
                    if key in t and t in title:
                        return items
        return []

    def _section_title_to_query_keywords(self, title: str) -> list[str]:
        """把章节标题映射到库查询关键词集"""
        title = (title or "").strip()
        if not title:
            return []
        for triggers, kws in self.SECTION_TITLE_KEYWORDS:
            if any(t in title for t in triggers):
                return kws
        # fallback：按 2 字滑窗切，长度 ≥ 2 的中文短语
        if len(title) <= 4:
            return [title]
        return [title[:2], title[2:4], title]

    async def _get_knowledge_reference(self, db: AsyncSession, section_title: str) -> str:
        """从知识库搜索与当前章节相关的样本/模板，作为 few-shot 参考。

        优先走 RAG 路径（语义检索 reference_embeddings.pkl）；
        如果索引未加载或检索失败，自动降级到关键词匹配。
        """
        # 路径 A: RAG 语义检索（首选）
        try:
            from app.services.embedding_service import embedding_service
            if embedding_service.is_loaded():
                rag_text = self._format_rag_reference_via_search(section_title, embedding_service)
                if rag_text:
                    return rag_text
        except Exception as e:
            logger.warning(f"[RAG] 检索失败，回退到关键词匹配: {e}")

        # 路径 B: 关键词 fallback
        return await self._keyword_reference_fallback(db, section_title)

    def _format_rag_reference_via_search(self, section_title: str, emb_svc) -> str:
        """语义检索 top-K 段并格式化为 prompt 片段。

        min_sim=0.45：vision 模型对纯文本的余弦相似度整体比专用文本 embedding 偏低，
        实测 0.45 是合理截断点（高于此一般是真相关，低于此噪音多）。
        """
        results = emb_svc.search(section_title, top_k=6, min_sim=0.45)
        if not results:
            return ""
        parts = ["【行业写作风格参考 — 模仿密度和具体度，不要照抄文字】"]
        for sim, meta, text in results:
            limit = 800
            preview = (text or "")[:limit]
            title = meta.get("title") or "(无标题)"
            source = meta.get("source") or ""
            parts.append(f"\n--- 参考：{title} （来源：{source}，相似度 {sim:.2f}）---")
            parts.append(preview)
            if text and len(text) > limit:
                parts.append(f"...（截取前 {limit} 字）")
        parts.append(f"\n（共 {len(results)} 段，按语义相关性排序）")
        return "\n".join(parts)

    async def _keyword_reference_fallback(self, db: AsyncSession, section_title: str) -> str:
        """关键词匹配 fallback（原 _get_knowledge_reference 实现）"""
        from sqlalchemy import or_, case

        keywords = self._section_title_to_query_keywords(section_title)
        if not keywords:
            return ""

        query = select(KnowledgeTemplate).where(KnowledgeTemplate.is_deleted == 0)
        conditions = []
        for kw in keywords[:3]:
            conditions.append(KnowledgeTemplate.title.contains(kw))
            conditions.append(KnowledgeTemplate.tags.contains(kw))
        if conditions:
            query = query.where(or_(*conditions))
        ref_priority = case((KnowledgeTemplate.category == 'REFERENCE', 0), else_=1)
        query = query.order_by(ref_priority, KnowledgeTemplate.usage_count.desc()).limit(2)

        result = await db.execute(query)
        templates = result.scalars().all()
        if not templates:
            return ""
        parts = ["【行业写作风格参考 — 模仿密度和具体度，不要照抄文字】"]
        for t in templates:
            limit = 1500 if t.category == 'REFERENCE' else 600
            content_preview = (t.content or "")[:limit]
            parts.append(f"\n--- 参考：{t.title} ---")
            parts.append(content_preview)
            if t.content and len(t.content) > limit:
                parts.append(f"...（截取前 {limit} 字）")
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
        if tender_requirements:
            tender_req = f"【招标要求】\n{tender_requirements}"
        else:
            tender_req = await self._get_tender_requirements(db, section.project_id)
        sections_ctx = await self._get_other_sections_context(db, section.project_id, section_id)
        knowledge_ref = await self._get_knowledge_reference(db, section.title)
        scoring_block = await self._get_scoring_items_for_section(db, section_id)
        checklist = self._section_title_to_checklist(section.title)

        additional_part = f"\n额外要求：\n{additional_context}" if additional_context else ""
        knowledge_part = f"\n{knowledge_ref}" if knowledge_ref else ""
        scoring_part = f"\n{scoring_block}\n" if scoring_block else ""
        # 把 checklist 转成填空骨架：AI 看到的是模板而不是要求
        checklist_part = ""
        if checklist:
            skeleton_lines = ["\n【本章节输出模板（必须严格按此骨架填空，所有 ## 一级标题缺一不可、不可合并、不可改名）】\n"]
            for item in checklist:
                # 每条 checklist 已经形如「一、子主题名（提示）」
                title_part = item.split("（")[0].strip()
                hint_part = "（" + item.split("（", 1)[1] if "（" in item else ""
                skeleton_lines.append(f"\n## {title_part}\n{hint_part}\n（在此展开 350-500 字：用 ### 1.1 / ### 1.2 拆分二级要点，每个 ### 下用（1）（2）（3）至少 3 个编号项，含 2 处以上量化指标和行业术语）\n")
            skeleton_lines.append(f"\n本章节合计 {len(checklist)} 个 ## 标题，必须**全部展开**，总字数 ≥2500（10 项时 ≥3500）。")
            skeleton_lines.append("\n警告：如果你只写了部分 ## 标题，会被判定为低质量作品。请逐条按骨架填空。")
            checklist_part = "\n".join(skeleton_lines) + "\n"

        prompt = f"""你是一个专业的标书编写助手。请为以下标书章节撰写内容。

标书项目：{project_title}
当前章节：{section.title}
{scoring_part}{checklist_part}
{sections_ctx}

{tender_req}

{company_info}
{knowledge_part}
{additional_part}

请撰写专业、详实的标书内容。**硬性要求（不达标视为低质量）**：

1. **必写子主题清单**：如上方有【本章节必写子主题清单】，**必须按顺序逐条作为 ## 一级标题**展开，每条独立成节 300-600 字。**不允许跳过、合并或重命名**。

2. **三级 markdown 结构（强制）**：
   - `## 一、子主题名` → `### 1.1 二级要点` → `（1）（2）（3）` 编号清单
   - 每个 `##` 至少 2 个 `###`，每个 `###` 至少 3 个 `（n）` 编号项
   - **严禁**单段超过 200 字而无小标题

3. **量化指标密度**（拿分关键）：本章节**累计至少 15 处**带数字+单位的具体指标，例如：
   - 工艺：「印刷误差 ≤0.2mm」「网点 175LPI」「墨层 0.02-0.03mm」「抗拉强度 ≥15N」「合格率 99.5%」
   - 时间：「24 小时」「1 小时响应」「48 小时研判」「30 分钟整改」
   - 环境：「温度 22-25℃」「湿度 ≤60%」「卡板间距 10cm」
   - 物料：「250g 牛皮纸」「80g 双胶纸」「0.2-0.25g/㎡ 涂布量」
   - **严禁**「较高质量」「丰富经验」「完善的体系」「一定的能力」「精准把控」「严格管控」这类形容词

4. **行业术语**：必用印刷行业术语（晒版/出片/套印/水墨平衡/网点/油墨密度/烫银/哑膜/覆膜/锁线/模切/卡板/瓦楞/包心折/CMYK/电化铝/无碳复写 等），密度不低于参考样本。

5. **逐条响应评分细则**：有【关联评分项】时，每条评分要素都要有 `### 响应：xxx` 段落对应。

6. **引用企业素材**：业绩按「项目名（甲方+金额万元+年份）」格式具体写；资质/设备/人员要写出**证书编号或型号**。

7. **模仿参考样本**：有【行业写作风格参考】时，模仿其密度和层级，重新组织文字，不照抄。

8. **篇幅**：**严格 ≥2500 字**（如有子主题清单 ≥3000 字）。AI 不允许提前结束，未达字数的章节会被打回重写。

9. **输出**：直接输出章节正文 markdown（章节大标题已有，不要重复），不带"以下是..."引导语。

⚠️ **反偷懒检测**：如果上方有【本章节输出模板】，你的输出**必须严格按骨架的所有 ## 一级标题逐个填写**：
- 不允许跳过任何 ## 标题（把 10 个变成 5 个 = 不合格）
- 不允许合并多个 ## 为一个（"一、A 和 B" = 不合格）
- 不允许只写到一半提前结束（写到 "## 五" 就不写 "## 六/七/八/九/十" = 不合格）
- 写完一个 ## 立刻继续下一个 ##，不要写"以上是xxx，下面继续"这种过渡语
- 必须用 markdown 三级层次：## → ### → （1）（2）（3）

写完后自检：你输出的 ## 数量是否等于模板要求的数量？字数是否 ≥2500？如不达标，请继续补全后再输出。"""

        client = self._get_client()
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个标书编写专家。当用户给出【输出模板骨架】时，你**必须**按骨架的所有 ## 一级标题逐条填写，不允许偷懒、跳过、合并标题或提前结束。每节都要写满 350+ 字，含具体工艺数字、行业术语和企业资料引用。整篇内容 ≥2500 字（如骨架有 10 项则 ≥3500 字）。优先保证完整性而非简洁性。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=8192,
            temperature=0.4,
        )

        return response.choices[0].message.content.strip()

    async def generate_section_content_stream(
        self,
        db: AsyncSession,
        section_id: int,
        tender_requirements: Optional[str] = None,
        additional_context: Optional[str] = None,
    ):
        """流式生成章节内容。

        Yield 类型：
          - dict {"content": "..."}        实时文本片段
          - dict {"progress": {...}}        多轮模式专用，节切换提示
          - dict {"section_done": {...}}    多轮模式专用，单节完成
          - str（向后兼容）                 视为 content（router 自动包装）

        路由：章节有 SECTION_CHECKLIST 且 ≥ 3 项 → 多轮生成；否则单轮 fallback。
        """
        section_result = await db.execute(
            select(BidSection).where(BidSection.id == section_id, BidSection.is_deleted == 0)
        )
        section = section_result.scalar_one_or_none()
        if not section:
            raise Exception("章节不存在")

        checklist = self._section_title_to_checklist(section.title)
        if checklist and len(checklist) >= 3:
            logger.info(f"[多轮生成] section={section_id} 「{section.title}」 子主题 {len(checklist)} 项")
            async for event in self._multi_turn_section_stream(
                db, section, checklist,
                tender_requirements=tender_requirements,
                additional_context=additional_context,
            ):
                yield event
        else:
            async for event in self._single_turn_section_stream(
                db, section,
                tender_requirements=tender_requirements,
                additional_context=additional_context,
            ):
                yield event

    # ── 单轮生成（回退路径，无 checklist 时用）────────────────

    async def _single_turn_section_stream(
        self, db: AsyncSession, section, *,
        tender_requirements: Optional[str] = None,
        additional_context: Optional[str] = None,
    ):
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
        sections_ctx = await self._get_other_sections_context(db, section.project_id, section.id)
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

请撰写专业、详实的标书内容（500-2500 字）。如有参考样本，模仿其密度和层级。直接输出 markdown 正文。"""

        client = self._get_client()
        stream = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个经验丰富的标书编写专家。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=8192,
            temperature=0.4,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"content": chunk.choices[0].delta.content}

    # ── 多轮生成（核心：每个 ## 子主题独立调一次 AI）──────────

    async def _multi_turn_section_stream(
        self, db: AsyncSession, section, checklist: list[str], *,
        tender_requirements: Optional[str] = None,
        additional_context: Optional[str] = None,
    ):
        # 1) 共享上下文（只查一次）
        company_info = await self._get_company_info(db)
        if tender_requirements:
            tender_req = f"【招标要求】\n{tender_requirements}"
        else:
            tender_req = await self._get_tender_requirements(db, section.project_id)
        scoring_block = await self._get_scoring_items_for_section(db, section.id)

        client = self._get_client()
        written: list[tuple[str, str]] = []  # [(标题, 末段 100 字), ...]
        total = len(checklist)

        for idx, item in enumerate(checklist):
            subtopic_title, subtopic_hint = self._parse_checklist_item(item)

            # 进度事件
            yield {"progress": {
                "current": idx + 1,
                "total": total,
                "subtopic": subtopic_title,
            }}

            # 子主题级 RAG 查询：按"章节标题 - 子主题 hint"作 query
            rag_query = f"{section.title} {subtopic_title} {subtopic_hint}".strip()
            rag_ref = await self._get_knowledge_reference(db, rag_query)

            prev_summary = self._format_prev_summary(written)
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

            section_buffer: list[str] = []
            try:
                stream = client.chat.completions.create(
                    model=settings.AI_MODEL,
                    messages=[
                        {"role": "system", "content": (
                            "你是标书撰写专家。当前任务是为指定的子主题深度展开 800-1500 字。"
                            "**只能写当前子主题**，不允许跨写其他子主题。"
                            "必须用三级 markdown（## → ### → 编号清单），含 ≥5 处量化指标和印刷行业术语。"
                            "优先保证篇幅与具体度。"
                        )},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=4096,
                    temperature=0.4,
                    stream=True,
                )
                # 段间分隔（除第一节外）
                if idx > 0:
                    yield {"content": "\n\n"}
                    section_buffer.append("\n\n")
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        section_buffer.append(text)
                        yield {"content": text}
            except Exception as e:
                logger.warning(f"[多轮生成] 子主题失败 {subtopic_title!r}: {e}")
                err = f"\n\n## {subtopic_title}\n\n（本节生成失败：{type(e).__name__}，请重新生成）\n\n"
                section_buffer = [err]
                yield {"content": err}

            # 累加供下节回顾
            full = "".join(section_buffer).strip()
            tail = full[-100:] if full else ""
            written.append((subtopic_title, tail))
            yield {"section_done": {
                "subtopic": subtopic_title,
                "word_count": len(full),
            }}

    # ── 多轮辅助 ──────────────────────────────────────────────

    @staticmethod
    def _parse_checklist_item(item: str) -> tuple[str, str]:
        """从 'X、xxx（hint）' 中切出 标题 / hint"""
        item = (item or "").strip()
        if "（" in item:
            idx = item.index("（")
            return item[:idx].strip(), item[idx:].strip()
        return item, ""

    @staticmethod
    def _format_prev_summary(written: list[tuple[str, str]]) -> str:
        if not written:
            return ""
        lines = ["【已写章节回顾】（确保当前节与前面衔接、不重复）"]
        for title, tail in written:
            snippet = tail.replace("\n", " ")[-80:]
            lines.append(f"- {title} ... {snippet}")
        return "\n".join(lines)

    def _build_subtopic_prompt(self, *, section_title: str, subtopic_title: str,
                                subtopic_hint: str, rag_ref: str, tender_req: str,
                                company_info: str, scoring_block: str,
                                prev_summary: str, additional_context: Optional[str]) -> str:
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
3. 三级 markdown 结构：
   - 顶层：## {subtopic_title}
   - 中层：### x.1 / ### x.2 / ### x.3 至少 2-3 个二级要点
   - 底层：（1）（2）（3）编号清单，每个 ### 至少 3 个编号项
4. 至少 5 处量化指标（数字+单位，如 ≤0.2mm / 7×24h / 22-25℃ / 99.5% / 250g/㎡）
   严禁"较高""丰富""完善""一定""精准把控""严格管控"等空话
5. 用印刷行业术语（晒版/出片/套印/水墨平衡/网点/油墨密度/烫银/哑膜/覆膜/锁线/模切/卡板/CMYK/电化铝等）
6. 引用企业素材时具体到「项目名（甲方+金额X.X万元+年X月）」格式
7. 模仿【行业写作风格参考】的密度和层级，但不照抄文字（重新组织）
8. 直接以 ## {subtopic_title} 开头，**只写本节**，不要写其他子主题
9. 不带"以下是..."引导语，不要总结，不要展望
""")
        return "\n".join(parts)

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
