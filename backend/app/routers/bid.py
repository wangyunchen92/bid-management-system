"""
标书编制路由 /api/v1/bid/*
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.bid import BidProjectCreate, BidProjectUpdate, BidSectionCreate, BidSectionUpdate, ReorderSectionsRequest
from app.services.bid_service import bid_service

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
