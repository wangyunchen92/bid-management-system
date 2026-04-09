"""
文档解析服务 — PDF/Word 文本提取
"""
import os
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber
from docx import Document


class DocumentParser:

    def extract_text(self, file_path: str) -> dict:
        """根据文件类型提取文本，返回 {text, page_count, tables_md}"""
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self.extract_from_pdf(file_path)
        elif ext == ".docx":
            return self.extract_from_docx(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def extract_from_pdf(self, file_path: str) -> dict:
        """PDF 文本提取：PyMuPDF 提文字 + pdfplumber 提表格"""
        # PyMuPDF 提取文字
        doc = fitz.open(file_path)
        pages_text = []
        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages_text.append(f"--- 第 {i+1} 页 ---\n{text}")
        page_count = len(doc)
        doc.close()

        # pdfplumber 提取表格
        tables_md = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            md = self._table_to_markdown(table)
                            if md:
                                tables_md.append(f"[第{i+1}页表格]\n{md}")
        except Exception:
            pass  # 表格提取失败不影响主流程

        full_text = "\n\n".join(pages_text)
        if tables_md:
            full_text += "\n\n=== 表格数据 ===\n\n" + "\n\n".join(tables_md)

        return {"text": full_text, "page_count": page_count, "tables_md": tables_md}

    def extract_from_docx(self, file_path: str) -> dict:
        """Word 文本提取"""
        doc = Document(file_path)
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                # 标题层级
                if "Heading" in (para.style.name or ""):
                    level = para.style.name.replace("Heading ", "")
                    try:
                        level_num = int(level)
                        paragraphs.append(f"{'#' * level_num} {para.text}")
                    except ValueError:
                        paragraphs.append(para.text)
                else:
                    paragraphs.append(para.text)

        # 提取表格
        tables_md = []
        for i, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                rows.append([cell.text for cell in row.cells])
            md = self._table_to_markdown(rows)
            if md:
                tables_md.append(f"[表格{i+1}]\n{md}")

        full_text = "\n".join(paragraphs)
        if tables_md:
            full_text += "\n\n=== 表格数据 ===\n\n" + "\n\n".join(tables_md)

        # Word 没有准确页数，估算
        page_count = max(1, len(full_text) // 2000)

        return {"text": full_text, "page_count": page_count, "tables_md": tables_md}

    def _table_to_markdown(self, table: list) -> str:
        """表格转 Markdown"""
        if not table or not table[0]:
            return ""
        # 清理 None
        cleaned = [[str(cell or "").strip() for cell in row] for row in table]
        # 跳过空行
        cleaned = [row for row in cleaned if any(cell for cell in row)]
        if not cleaned:
            return ""

        header = "| " + " | ".join(cleaned[0]) + " |"
        separator = "| " + " | ".join("---" for _ in cleaned[0]) + " |"
        rows = ["| " + " | ".join(row) + " |" for row in cleaned[1:]]
        return "\n".join([header, separator] + rows)


document_parser = DocumentParser()
