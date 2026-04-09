"""
标书导出服务 — 生成 Word 文件
"""
import io
import os
from datetime import datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bid import BidProject, BidSection

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "exports")


class BidExportService:

    async def export_to_word(self, db: AsyncSession, project_id: int) -> str:
        """导出标书为 Word 文件，返回文件路径"""
        # 查询项目
        project_result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise Exception("标书项目不存在")

        # 查询所有章节（树形展开）
        sections_result = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project_id, BidSection.is_deleted == 0
            ).order_by(BidSection.sort_order.asc(), BidSection.id.asc())
        )
        sections = sections_result.scalars().all()

        # 构建 Word 文档
        doc = Document()

        # 设置默认字体
        style = doc.styles['Normal']
        font = style.font
        font.name = '宋体'
        font.size = Pt(12)

        # 标题
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(project.title)
        run.font.size = Pt(22)
        run.font.bold = True
        run.font.name = '黑体'

        doc.add_paragraph()  # 空行

        # 按树形结构写入章节
        section_map = {s.id: s for s in sections}
        root_sections = [s for s in sections if s.parent_id is None or s.parent_id not in section_map]
        child_map = {}
        for s in sections:
            if s.parent_id and s.parent_id in section_map:
                child_map.setdefault(s.parent_id, []).append(s)

        def write_section(section, level=1):
            # 标题
            heading = doc.add_heading(section.title, level=min(level, 4))
            # 内容
            if section.content:
                for para_text in section.content.split('\n'):
                    if para_text.strip():
                        p = doc.add_paragraph(para_text.strip())
                        p.paragraph_format.first_line_indent = Cm(0.74)  # 首行缩进2字符
                        p.paragraph_format.line_spacing = 1.5

            # 子章节
            children = child_map.get(section.id, [])
            for child in children:
                write_section(child, level + 1)

        for root in root_sections:
            write_section(root)

        # 保存
        os.makedirs(EXPORT_DIR, exist_ok=True)
        filename = f"{project.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        # 清理文件名中的特殊字符
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.', '（', '）')).strip()
        if not safe_filename.endswith('.docx'):
            safe_filename += '.docx'
        filepath = os.path.join(EXPORT_DIR, safe_filename)
        doc.save(filepath)

        return filepath

    def _build_doc(self, project_title: str, sections: list, section_map: dict, child_map: dict) -> Document:
        """构建 Word Document 对象（公共逻辑）"""
        doc = Document()

        # 设置默认字体
        style = doc.styles['Normal']
        font = style.font
        font.name = '宋体'
        font.size = Pt(12)

        # 封面标题
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(project_title)
        run.font.size = Pt(22)
        run.font.bold = True
        run.font.name = '黑体'
        doc.add_paragraph()  # 空行
        doc.add_page_break()

        # 目录页
        doc.add_heading('目录', level=1)
        root_sections = [s for s in sections if s.parent_id is None or s.parent_id not in section_map]
        for s in root_sections:
            doc.add_paragraph(s.title, style='List Bullet')
            for child in child_map.get(s.id, []):
                p = doc.add_paragraph(f"  {child.title}", style='List Bullet')
        doc.add_page_break()

        # 正文
        def write_section(section, level=1):
            doc.add_heading(section.title, level=min(level, 4))
            if section.content:
                for para_text in section.content.split('\n'):
                    if para_text.strip():
                        p = doc.add_paragraph(para_text.strip())
                        p.paragraph_format.first_line_indent = Cm(0.74)
                        p.paragraph_format.line_spacing = 1.5
            for child in child_map.get(section.id, []):
                write_section(child, level + 1)

        for root in root_sections:
            write_section(root)

        return doc

    async def get_project_title(self, db: AsyncSession, project_id: int) -> str:
        """获取项目标题，用于文件命名"""
        result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        project = result.scalar_one_or_none()
        return project.title if project else f"标书_{project_id}"

    async def export_to_word_stream(self, db: AsyncSession, project_id: int) -> io.BytesIO:
        """导出标书为 Word，返回内存流（StreamingResponse 专用）"""
        project_result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise Exception("标书项目不存在")

        sections_result = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project_id, BidSection.is_deleted == 0
            ).order_by(BidSection.sort_order.asc(), BidSection.id.asc())
        )
        sections = sections_result.scalars().all()

        section_map = {s.id: s for s in sections}
        child_map = {}
        for s in sections:
            if s.parent_id and s.parent_id in section_map:
                child_map.setdefault(s.parent_id, []).append(s)

        doc = self._build_doc(project.title, sections, section_map, child_map)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer


bid_export_service = BidExportService()
