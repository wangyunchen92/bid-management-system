"""
开标跟踪路由 /api/v1/opening/*
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.opening import OpeningCreate, OpeningUpdate
from app.services.opening_service import opening_service

router = APIRouter()


@router.get("/list", summary="开标记录列表")
async def list_openings(
    params: PaginationParams = Depends(get_pagination_params),
    keyword: Optional[str] = Query(default=None, description="招标标题关键词"),
    result: Optional[str] = Query(default=None, description="开标结果 WIN/LOSE/INVALID/ABORTED"),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await opening_service.list_openings(db, params, keyword=keyword, result=result)
    return page_response(items=data["items"], total=data["total"], page=data["page"], page_size=data["page_size"])


@router.post("", summary="创建开标记录")
async def create_opening(
    data: OpeningCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await opening_service.create_opening(db, data, user_id)
    return success(data=result, message="创建成功")


@router.get("/by-tender/{tender_id}", summary="按招标查询开标记录")
async def get_by_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await opening_service.get_by_tender(db, tender_id)
    return success(data=data)


@router.get("/{opening_id}", summary="开标记录详情")
async def get_opening(
    opening_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await opening_service.get_opening(db, opening_id)
    return success(data=data)


@router.put("/{opening_id}", summary="更新开标记录")
async def update_opening(
    opening_id: int,
    data: OpeningUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await opening_service.update_opening(db, opening_id, data, user_id)
    return success(data=result, message="更新成功")


@router.delete("/{opening_id}", summary="删除开标记录")
async def delete_opening(
    opening_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await opening_service.delete_opening(db, opening_id, user_id)
    return success(message="删除成功")
