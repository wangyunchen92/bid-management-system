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
from app.models.tender import Tender
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

    async def save_to_tender(self, db: AsyncSession, doc_id: int, user_id: int) -> dict:
        """将解析结果保存到招标信息（更新已有或创建新的）"""
        result = await db.execute(
            select(TenderDocument).where(TenderDocument.id == doc_id, TenderDocument.is_deleted == 0)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundException("文档不存在")
        if doc.parse_status != "COMPLETED" or not doc.parse_result:
            raise BusinessException("文档尚未解析完成")

        parse_result = json.loads(doc.parse_result)
        basic = parse_result.get("basic_info", {})
        timeline = parse_result.get("timeline", {})

        def parse_datetime(s):
            """将字符串转为 datetime 对象，SQLite 需要"""
            if not s:
                return None
            from dateutil import parser as dateutil_parser
            try:
                return dateutil_parser.parse(s)
            except Exception:
                # 尝试常见中文日期格式
                import re
                m = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日]?\s*(\d{1,2})?[:]?(\d{1,2})?', s)
                if m:
                    parts = [int(x) for x in m.groups() if x]
                    while len(parts) < 5:
                        parts.append(0)
                    return datetime(parts[0], parts[1], parts[2], parts[3], parts[4])
                return None

        # 构建招标信息数据
        tender_data = {}
        if basic.get("project_name"):
            tender_data["title"] = basic["project_name"]
        if basic.get("tender_no"):
            tender_data["tender_no"] = basic["tender_no"]
        if basic.get("tender_unit"):
            tender_data["tender_unit"] = basic["tender_unit"]
        if basic.get("tender_method"):
            method_map = {"公开招标": "PUBLIC", "邀请招标": "INVITE", "竞争性谈判": "NEGOTIATE", "询价": "INQUIRY", "单一来源": "SINGLE"}
            tender_data["tender_method"] = method_map.get(basic["tender_method"], basic["tender_method"])
        if basic.get("budget_amount") is not None:
            tender_data["budget_amount"] = basic["budget_amount"]
        if timeline.get("bid_deadline"):
            dt = parse_datetime(timeline["bid_deadline"])
            if dt:
                tender_data["reg_deadline"] = dt
        if timeline.get("open_bid_time"):
            dt = parse_datetime(timeline["open_bid_time"])
            if dt:
                tender_data["open_bid_time"] = dt
        if timeline.get("deposit_amount") is not None:
            tender_data["deposit_amount"] = timeline["deposit_amount"]
        if timeline.get("deposit_deadline"):
            dt = parse_datetime(timeline["deposit_deadline"])
            if dt:
                tender_data["deposit_deadline"] = dt

        if doc.tender_id:
            # 更新已有招标信息
            tender_result = await db.execute(
                select(Tender).where(Tender.id == doc.tender_id, Tender.is_deleted == 0)
            )
            tender = tender_result.scalar_one_or_none()
            if tender:
                for key, value in tender_data.items():
                    setattr(tender, key, value)
                tender.updated_by = user_id
                await db.flush()
                await db.refresh(tender)
                return {"tender_id": tender.id, "action": "updated", "fields_updated": list(tender_data.keys())}

        # 创建新招标信息
        tender_data["status"] = "PENDING"
        tender_data["created_by"] = user_id
        tender_data["updated_by"] = user_id
        tender = Tender(**tender_data)
        db.add(tender)
        await db.flush()
        await db.refresh(tender)

        # 关联文档到新招标
        doc.tender_id = tender.id
        await db.flush()

        return {"tender_id": tender.id, "action": "created", "fields_updated": list(tender_data.keys())}

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
