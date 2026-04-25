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
    FrameworkFromTenderRequest,
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


@router.post("/projects/{project_id}/framework-from-tender", summary="基于招标文件抽取模板生成框架（SSE流式）")
async def generate_framework_from_tender(
    project_id: int,
    data: FrameworkFromTenderRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """基于招标文件解析结果，AI 抽取每章模板原文并生成章节框架。SSE 流式推送进度。"""
    from app.services.bid_framework_service import bid_framework_service

    async def event_generator():
        try:
            async for event in bid_framework_service.generate_from_tender(
                db, project_id, data.tender_doc_id, user_id
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ========== 填充资料库章节 ==========

@router.post("/projects/{project_id}/fill-library-sections", summary="一键填充资料库章节")
async def fill_library_sections(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """从企业资料库自动填充 LIBRARY 类型章节（资质、业绩、人员、设备）"""
    from app.models.bid import BidSection
    from app.models.library import Qualification, Achievement, PersonnelCert, Product

    # 查所有 LIBRARY 章节
    result = await db.execute(
        select(BidSection).where(
            BidSection.project_id == project_id,
            BidSection.section_type == "LIBRARY",
            BidSection.is_deleted == 0,
        ).order_by(BidSection.sort_order.asc())
    )
    sections = result.scalars().all()
    if not sections:
        return success(data=[], message="没有 LIBRARY 类型章节")

    filled = []

    for section in sections:
        title = section.title
        content_parts = []

        # 根据章节标题匹配对应的资料库数据（业绩优先于资质，避免"业绩证明材料"误匹配）
        if any(kw in title for kw in ["业绩", "合同", "案例"]):
            achvs = (await db.execute(
                select(Achievement).where(Achievement.is_deleted == 0)
                .order_by(Achievement.contract_amount.desc())
            )).scalars().all()
            if achvs:
                content_parts.append("业绩证明材料清单：\n")
                for i, a in enumerate(achvs, 1):
                    line = f"{i}. {a.project_name}"
                    if a.client_name:
                        line += f"\n   甲方：{a.client_name}"
                    if a.contract_amount:
                        line += f"\n   合同金额：{float(a.contract_amount)}万元"
                    if a.completion_date:
                        line += f"\n   完成时间：{a.completion_date}"
                    if a.description:
                        line += f"\n   项目内容：{a.description}"
                    if a.file_path:
                        line += f"\n   [附件:{a.file_path}:{a.project_name}]"
                    else:
                        line += f"\n   （待上传合同扫描件）"
                    content_parts.append(line)

        elif any(kw in title for kw in ["财务", "审计", "纳税", "社保"]):
            content_parts.append("财务状况证明材料：\n")
            content_parts.append("（请上传以下材料扫描件）")
            content_parts.append("1. 近三年审计报告")
            content_parts.append("2. 近三个月纳税证明")
            content_parts.append("3. 近三个月社保缴纳证明")

        elif any(kw in title for kw in ["资质", "营业执照", "许可证", "证明材料"]):
            quals = (await db.execute(
                select(Qualification).where(Qualification.is_deleted == 0)
            )).scalars().all()
            if quals:
                content_parts.append("企业资质证明材料清单：\n")
                for i, q in enumerate(quals, 1):
                    line = f"{i}. {q.cert_name}"
                    if q.cert_type:
                        line += f"（{q.cert_type}）"
                    if q.cert_no:
                        line += f"\n   证书编号：{q.cert_no}"
                    if q.issuing_authority:
                        line += f"\n   发证机关：{q.issuing_authority}"
                    if q.issue_date:
                        line += f"\n   发证日期：{q.issue_date}"
                    if q.expiry_date:
                        line += f"\n   有效期至：{q.expiry_date}"
                    if q.remark:
                        line += f"\n   备注：{q.remark}"
                    if q.file_path:
                        line += f"\n   [附件:{q.file_path}:{q.cert_name}]"
                    content_parts.append(line)

        elif any(kw in title for kw in ["人员", "团队", "项目组"]):
            certs = (await db.execute(
                select(PersonnelCert).where(PersonnelCert.is_deleted == 0)
            )).scalars().all()
            if certs:
                content_parts.append("项目团队人员配备：\n")
                for i, c in enumerate(certs, 1):
                    line = f"{i}. {c.person_name}"
                    if c.cert_name:
                        line += f" — {c.cert_name}"
                    if c.cert_no:
                        line += f"（{c.cert_no}）"
                    if c.remark:
                        line += f"\n   {c.remark}"
                    content_parts.append(line)
            else:
                content_parts.append("项目团队人员配备：\n（请在企业资料库中添加人员证书信息）")

        elif any(kw in title for kw in ["设备", "机器", "产品"]):
            prods = (await db.execute(
                select(Product).where(Product.is_deleted == 0)
            )).scalars().all()
            if prods:
                content_parts.append("设备配备清单：\n")
                for i, p in enumerate(prods, 1):
                    line = f"{i}. {p.name}"
                    if p.brand:
                        line += f"\n   品牌：{p.brand}"
                    if p.model:
                        line += f"\n   型号：{p.model}"
                    if p.quantity:
                        line += f"\n   数量：{p.quantity}{p.unit or '台'}"
                    if p.description:
                        line += f"\n   说明：{p.description}"
                    if p.file_path:
                        line += f"\n   [附件:{p.file_path}:{p.name}]"
                    content_parts.append(line)

        # 填充内容
        if content_parts:
            content = "\n".join(content_parts)
            section.content = content
            section.word_count = len(content)
            section.status = "COMPLETED"
            section.updated_by = user_id
            await db.flush()
            filled.append({
                "id": section.id,
                "title": section.title,
                "word_count": len(content),
            })

    return success(
        data=filled,
        message=f"已填充 {len(filled)} 个资料库章节" if filled else "资料库暂无数据可填充"
    )


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


@router.get("/projects/{project_id}/preview", summary="整体文档预览")
async def preview_document(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    """返回整体文档预览内容（所有章节按顺序拼接）"""
    from app.models.bid import BidProject, BidSection

    # 查项目
    proj_result = await db.execute(
        select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise Exception("项目不存在")

    # 查所有章节
    sec_result = await db.execute(
        select(BidSection).where(
            BidSection.project_id == project_id,
            BidSection.is_deleted == 0,
        ).order_by(BidSection.sort_order.asc())
    )
    sections = sec_result.scalars().all()

    section_list = []
    total_words = 0
    completed = 0
    for s in sections:
        word_count = len(s.content) if s.content else 0
        total_words += word_count
        if s.status == "COMPLETED":
            completed += 1
        section_list.append({
            "id": s.id,
            "title": s.title,
            "content": s.content or "",
            "section_type": s.section_type,
            "status": s.status,
            "word_count": word_count,
            "sort_order": s.sort_order,
        })

    return success(data={
        "project_title": project.title,
        "total_sections": len(sections),
        "completed_sections": completed,
        "total_words": total_words,
        "sections": section_list,
    })


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
