"""
招标文件管理服务 — 上传、提取、AI 解析
"""
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import BusinessException, NotFoundException
from app.config import settings
from app.models.tender_document import TenderDocument
from app.services.document_parser import document_parser
from app.services.tender_ai_parser import tender_ai_parser

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class TenderDocService:

    async def upload_and_parse(self, db: AsyncSession, file: UploadFile, user_id: int,
                                project_id: int = None, tender_id: int = None) -> dict:
        """上传文件 + 提取文本 + AI 解析（同步）"""

        # 1. 验证文件
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise BusinessException(f"不支持的文件格式 {ext}，仅支持 PDF 和 DOCX")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise BusinessException(f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）")

        # 2. 保存文件
        file_id = str(uuid.uuid4())
        rel_dir = os.path.join("tender_docs", datetime.now().strftime("%Y%m"))
        abs_dir = os.path.join(UPLOAD_DIR, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        stored_filename = f"{file_id}{ext}"
        stored_path = os.path.join(rel_dir, stored_filename)
        abs_path = os.path.join(abs_dir, stored_filename)

        with open(abs_path, "wb") as f:
            f.write(content)

        # 3. 创建数据库记录
        doc = TenderDocument(
            project_id=project_id,
            tender_id=tender_id,
            original_name=file.filename,
            stored_path=stored_path,
            file_size=len(content),
            file_type=ext.lstrip("."),
            parse_status="EXTRACTING",
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)

        # 4. 提取文本
        try:
            extract_result = document_parser.extract_text(abs_path)
            doc.page_count = extract_result["page_count"]
            doc.raw_text = extract_result["text"]
            doc.parse_status = "PARSING"
            await db.flush()
        except Exception as e:
            doc.parse_status = "FAILED"
            doc.error_message = f"文本提取失败: {str(e)}"
            await db.flush()
            logger.error(f"文本提取失败: {e}")
            return self._doc_to_dict(doc)

        # 5. AI 解析
        try:
            parse_result = tender_ai_parser.parse(extract_result["text"])
            doc.parse_result = json.dumps(parse_result, ensure_ascii=False)
            doc.parse_status = "COMPLETED"
            await db.flush()
        except Exception as e:
            doc.parse_status = "FAILED"
            doc.error_message = f"AI 解析失败: {str(e)}"
            await db.flush()
            logger.error(f"AI 解析失败: {e}")

        await db.refresh(doc)
        return self._doc_to_dict(doc)

    async def get_document(self, db: AsyncSession, doc_id: int) -> dict:
        result = await db.execute(
            select(TenderDocument).where(TenderDocument.id == doc_id, TenderDocument.is_deleted == 0)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundException("文档不存在")
        return self._doc_to_dict(doc)

    async def list_by_project(self, db: AsyncSession, project_id: int) -> list:
        result = await db.execute(
            select(TenderDocument).where(
                TenderDocument.project_id == project_id, TenderDocument.is_deleted == 0
            ).order_by(TenderDocument.id.desc())
        )
        return [self._doc_to_dict(d) for d in result.scalars().all()]

    async def list_by_tender(self, db: AsyncSession, tender_id: int) -> list:
        result = await db.execute(
            select(TenderDocument).where(
                TenderDocument.tender_id == tender_id, TenderDocument.is_deleted == 0
            ).order_by(TenderDocument.id.desc())
        )
        return [self._doc_to_dict(d) for d in result.scalars().all()]

    async def delete_document(self, db: AsyncSession, doc_id: int, user_id: int) -> None:
        result = await db.execute(
            select(TenderDocument).where(TenderDocument.id == doc_id, TenderDocument.is_deleted == 0)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundException("文档不存在")
        doc.is_deleted = 1
        doc.updated_by = user_id
        await db.flush()

    def _doc_to_dict(self, doc: TenderDocument) -> dict:
        d = {
            "id": doc.id,
            "project_id": doc.project_id,
            "tender_id": doc.tender_id,
            "original_name": doc.original_name,
            "file_size": doc.file_size,
            "file_type": doc.file_type,
            "page_count": doc.page_count,
            "parse_status": doc.parse_status,
            "parse_result": json.loads(doc.parse_result) if doc.parse_result else None,
            "error_message": doc.error_message,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        return d


tender_doc_service = TenderDocService()
