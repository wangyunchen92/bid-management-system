"""
标书编制路由 /api/v1/bid/*
"""

import io
import json
import os
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.bid import (
    BidProjectCreate, BidProjectUpdate,
    BidSectionCreate, BidSectionUpdate,
    ReorderSectionsRequest,
    AIGenerateRequest, AIGenerateResponse,
    BidCheckRequest,
)
from app.services.bid_service import bid_service
from app.services.bid_ai_service import bid_ai_service
from app.services.bid_export_service import bid_export_service

router = APIRouter()


# ========== 标书项目 ==========

@router.get("/projects", summary="标书项目列表")
async def list_projects(
    params: PaginationParams = Depends(get_pagination_params),
    keyword: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    leader_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await bid_service.list_projects(db, params, keyword=keyword, status=status, leader_id=leader_id)
    return page_response(items=result["items"], total=result["total"], page=result["page"], page_size=result["page_size"])


@router.post("/projects", summary="创建标书项目")
async def create_project(
    data: BidProjectCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await bid_service.create_project(db, data, user_id)
    return success(data=result, message="创建成功")


@router.get("/projects/by-tender/{tender_id}", summary="按招标查标书项目")
async def get_by_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await bid_service.get_by_tender(db, tender_id)
    return success(data=result)


@router.get("/projects/{project_id}", summary="标书项目详情")
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await bid_service.get_project(db, project_id)
    return success(data=result)


@router.put("/projects/{project_id}", summary="更新标书项目")
async def update_project(
    project_id: int,
    data: BidProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await bid_service.update_project(db, project_id, data, user_id)
    return success(data=result, message="更新成功")


@router.delete("/projects/{project_id}", summary="删除标书项目")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await bid_service.delete_project(db, project_id, user_id)
    return success(message="删除成功")


# ========== 标书章节 ==========

@router.get("/projects/{project_id}/sections", summary="章节树")
async def get_section_tree(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await bid_service.get_section_tree(db, project_id)
    return success(data=result)


@router.put("/projects/{project_id}/sections/reorder", summary="章节排序")
async def reorder_sections(
    project_id: int,
    data: ReorderSectionsRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await bid_service.reorder_sections(db, project_id, data.section_ids, user_id)
    return success(data=result, message="排序更新成功")


@router.post("/sections", summary="创建章节")
async def create_section(
    data: BidSectionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await bid_service.create_section(db, data, user_id)
    return success(data=result, message="创建成功")


@router.get("/sections/{section_id}", summary="章节详情")
async def get_section(
    section_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await bid_service.get_section(db, section_id)
    return success(data=result)


@router.put("/sections/{section_id}", summary="更新章节")
async def update_section(
    section_id: int,
    data: BidSectionUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await bid_service.update_section(db, section_id, data, user_id)
    return success(data=result, message="更新成功")


@router.delete("/sections/{section_id}", summary="删除章节")
async def delete_section(
    section_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await bid_service.delete_section(db, section_id, user_id)
    return success(message="删除成功")


# ========== 框架生成 ==========

@router.post("/projects/{project_id}/generate-framework", summary="一键生成标书框架")
async def generate_framework(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """根据标准模板+知识库自动生成标书章节框架"""
    from app.services.bid_framework_service import bid_framework_service
    sections = await bid_framework_service.generate_framework(db, project_id, user_id)
    return success(data=sections, message=f"已生成 {len(sections)} 个章节")


# ========== 批量 AI 生成 ==========

@router.post("/projects/{project_id}/batch-ai-generate", summary="批量生成所有AI章节")
async def batch_ai_generate(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """SSE 流式批量生成所有 AI_GENERATE 类型章节"""
    from app.models.bid import BidSection

    # 查所有 AI_GENERATE 章节
    result = await db.execute(
        select(BidSection).where(
            BidSection.project_id == project_id,
            BidSection.section_type == "AI_GENERATE",
            BidSection.is_deleted == 0,
        ).order_by(BidSection.sort_order.asc())
    )
    sections = result.scalars().all()

    if not sections:
        return success(data=[], message="没有需要 AI 生成的章节")

    async def event_generator():
        for i, section in enumerate(sections):
            # 通知前端当前进度
            yield f"data: {json.dumps({'type': 'progress', 'current': i+1, 'total': len(sections), 'section_title': section.title}, ensure_ascii=False)}\n\n"

            # 生成内容
            try:
                content = await bid_ai_service.generate_section_content(db, section.id)
                # 保存到章节
                section.content = content
                section.word_count = len(content)
                section.status = "COMPLETED"
                await db.flush()

                yield f"data: {json.dumps({'type': 'section_done', 'section_id': section.id, 'section_title': section.title, 'word_count': len(content)}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'section_error', 'section_id': section.id, 'section_title': section.title, 'error': str(e)}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'total': len(sections)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ========== AI 功能 ==========

@router.post("/sections/{section_id}/ai-generate", summary="AI 生成章节内容")
async def ai_generate_section(
    section_id: int,
    data: AIGenerateRequest = AIGenerateRequest(),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """调用 AI 为指定章节生成内容初稿，返回 generated_content（不自动保存）"""
    content = await bid_ai_service.generate_section_content(
        db,
        section_id,
        tender_requirements=data.tender_requirements,
        additional_context=data.additional_context,
    )
    return success(data={"generated_content": content}, message="AI 内容已生成")


@router.post("/sections/{section_id}/ai-generate-stream", summary="AI 流式生成章节内容")
async def ai_generate_section_stream(
    section_id: int,
    data: AIGenerateRequest = AIGenerateRequest(),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """SSE 流式生成，前端实时接收文本片段"""
    async def event_generator():
        try:
            async for chunk in bid_ai_service.generate_section_content_stream(
                db, section_id,
                tender_requirements=data.tender_requirements,
                additional_context=data.additional_context,
            ):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/projects/{project_id}/compliance-check", summary="废标检查（旧路由，兼容保留）")
@router.post("/projects/{project_id}/check", summary="废标检查")
async def compliance_check(
    project_id: int,
    data: BidCheckRequest = BidCheckRequest(),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """AI 对照招标要求检查标书合规性，返回逐条检查结果"""
    result = await bid_ai_service.check_bid_compliance(
        db,
        project_id,
        tender_requirements=data.tender_requirements,
    )
    return success(data=result)


@router.get("/projects/{project_id}/export-word", summary="导出 Word（旧路由，兼容保留）")
@router.get("/projects/{project_id}/export", summary="导出 Word")
async def export_word(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """导出标书为 Word 文件（StreamingResponse）"""
    file_buffer = await bid_export_service.export_to_word_stream(db, project_id)
    project_title = await bid_export_service.get_project_title(db, project_id)
    filename = f"{project_title}.docx"
    # RFC 5987 编码，支持中文文件名
    encoded_name = quote(filename, safe="")
    return StreamingResponse(
        file_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )
