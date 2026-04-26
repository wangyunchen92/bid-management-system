"""
招标文件管理服务 — 上传、提取、AI 解析
"""
import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

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

    async def upload_and_parse_stream(self, db: AsyncSession, content: bytes, filename: str, user_id: int,
                                       project_id: int = None, tender_id: int = None) -> AsyncGenerator[dict, None]:
        """上传并解析（SSE 流式版本，推送进度事件）

        注意：file content 必须在调用前读出，因为 generator 异步执行时
        multipart 上传文件会被关闭。
        """
        # 1. 验证文件
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            yield {"type": "error", "message": f"不支持的文件格式 {ext}，仅支持 PDF 和 DOCX"}
            return

        if len(content) > MAX_FILE_SIZE:
            yield {"type": "error", "message": f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）"}
            return

        yield {"type": "uploading", "message": "保存文件..."}

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
            project_id=project_id, tender_id=tender_id,
            original_name=filename, stored_path=stored_path,
            file_size=len(content), file_type=ext.lstrip("."),
            parse_status="EXTRACTING",
            created_by=user_id, updated_by=user_id,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        doc_id = doc.id

        # 流水线总耗时埋点
        t_pipeline_start = time.perf_counter()
        timings = {"file_size_kb": round(len(content) / 1024, 1)}

        yield {"type": "extracting", "message": "提取文本..."}

        # 4. 提取文本
        t_extract0 = time.perf_counter()
        try:
            extract_result = await asyncio.to_thread(document_parser.extract_text, abs_path)
            doc.page_count = extract_result["page_count"]
            text = extract_result["text"]
            timings["extract"] = round(time.perf_counter() - t_extract0, 2)
            timings.update(extract_result.get("timing", {}))
        except Exception as e:
            doc.parse_status = "FAILED"
            doc.error_message = f"文本提取失败: {str(e)}"
            await db.flush()
            await db.commit()
            logger.error(f"文本提取失败: {e}")
            yield {"type": "error", "message": str(e)}
            return

        # 4.5 扫描件检测 + 视觉 OCR 兜底
        avg_chars_per_page = len(text) / max(doc.page_count, 1)
        if ext == ".pdf" and avg_chars_per_page < 50:
            total_pages = doc.page_count
            pages_to_process = min(total_pages, 100)
            yield {
                "type": "ocr_start",
                "total_pages": total_pages,
                "pages_to_process": pages_to_process,
                "message": f"检测到扫描件，开始 OCR（共 {total_pages} 页，处理前 {pages_to_process} 页）",
            }
            doc.parse_status = "OCR"
            await db.flush()
            await db.commit()

            t_ocr0 = time.perf_counter()
            all_text = []
            for i in range(pages_to_process):
                yield {
                    "type": "ocr_page",
                    "current": i + 1,
                    "total": pages_to_process,
                    "message": f"OCR 第 {i + 1}/{pages_to_process} 页...",
                }
                try:
                    page_text = await asyncio.to_thread(tender_ai_parser.ocr_single_page, abs_path, i)
                    all_text.append(f"--- 第 {i+1} 页 ---\n{page_text}")
                    logger.info(f"OCR 第 {i+1}/{pages_to_process} 页完成（{len(page_text)} 字）")
                except Exception as e:
                    logger.warning(f"OCR 第 {i+1} 页失败: {e}")
                    all_text.append(f"--- 第 {i+1} 页 ---\n[OCR 失败]")
                    yield {"type": "ocr_page_failed", "page": i + 1, "error": str(e)}

            text = "\n\n".join(all_text)
            if total_pages > pages_to_process:
                text += f"\n\n[文档共 {total_pages} 页，仅处理了前 {pages_to_process} 页]"
            timings["ocr_total"] = round(time.perf_counter() - t_ocr0, 2)
            timings["ocr_pages"] = pages_to_process
            timings["ocr_avg_per_page"] = round(timings["ocr_total"] / max(pages_to_process, 1), 2)
            logger.info(
                f"[TIMING] OCR 全部完成: 总 {timings['ocr_total']}s | {pages_to_process} 页 | 均 {timings['ocr_avg_per_page']}s/页"
            )
            yield {"type": "ocr_done", "message": f"OCR 完成（{len(text)} 字）"}

        doc.raw_text = text
        doc.parse_status = "PARSING"
        await db.flush()
        await db.commit()

        yield {"type": "parsing", "message": "AI 解析中..."}

        # 5. AI 解析
        t_ai0 = time.perf_counter()
        try:
            parse_result = await asyncio.to_thread(tender_ai_parser.parse, text)
            timings["ai_parse"] = round(time.perf_counter() - t_ai0, 2)
            doc.parse_result = json.dumps(parse_result, ensure_ascii=False)
            doc.parse_status = "COMPLETED"
            await db.flush()
            await db.commit()
        except Exception as e:
            doc.parse_status = "FAILED"
            doc.error_message = f"AI 解析失败: {str(e)}"
            await db.flush()
            await db.commit()
            logger.error(f"AI 解析失败: {e}")
            yield {"type": "error", "message": str(e)}
            return

        await db.refresh(doc)

        # 6. 自动保存到招标信息（如果尚未关联）
        try:
            yield {"type": "linking", "message": "自动保存到招标信息..."}
            link_result = await self.save_to_tender(db, doc.id, user_id)
            await db.commit()
            await db.refresh(doc)
            yield {
                "type": "linked",
                "tender_id": link_result["tender_id"],
                "action": link_result["action"],
                "message": f"已{('更新' if link_result['action'] == 'updated' else '创建')}招标信息（{len(link_result['fields_updated'])} 个字段）",
            }
        except Exception as e:
            logger.warning(f"自动保存到招标信息失败（不影响解析）: {e}")
            yield {"type": "link_failed", "message": f"自动关联失败：{str(e)[:100]}"}

        timings["pipeline_total"] = round(time.perf_counter() - t_pipeline_start, 2)
        logger.info(f"[TIMING] 招标文件解析流水线完成: {timings}")
        yield {"type": "done", "doc": self._doc_to_dict(doc), "timing": timings}

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
            text = extract_result["text"]

            # 扫描件检测：每页平均文本 < 50 字 → 视为扫描件，启用视觉 OCR 兜底
            avg_chars_per_page = len(text) / max(doc.page_count, 1)
            if ext == ".pdf" and avg_chars_per_page < 50:
                logger.info(f"检测到扫描件 PDF（{doc.page_count} 页平均 {avg_chars_per_page:.0f} 字/页），启用视觉 OCR")
                doc.parse_status = "OCR"
                await db.flush()
                try:
                    text = tender_ai_parser.ocr_pdf_with_vision(abs_path, max_pages=100)
                    logger.info(f"OCR 完成，共 {len(text)} 字")
                except Exception as ocr_err:
                    logger.warning(f"视觉 OCR 失败，使用原始文本: {ocr_err}")

            doc.raw_text = text
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
            parse_result = tender_ai_parser.parse(text)
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
