"""
招标管理路由 /api/v1/tender/*
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.tender import TenderCreate, TenderUpdate, UpdateStatusRequest, UpdateFollowerRequest
from app.services.tender_service import tender_service

router = APIRouter()


@router.get("/list", summary="招标列表")
async def list_tenders(
    params: PaginationParams = Depends(get_pagination_params),
    keyword: Optional[str] = Query(default=None),
    tender_method: Optional[str] = Query(default=None),
    info_source: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    follower_id: Optional[int] = Query(default=None),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await tender_service.list_tenders(
        db, params, keyword=keyword, tender_method=tender_method,
        info_source=info_source, status=status, follower_id=follower_id,
        start_date=start_date, end_date=end_date,
    )
    return page_response(items=result["items"], total=result["total"], page=result["page"], page_size=result["page_size"])


@router.post("", summary="创建招标信息")
async def create_tender(
    data: TenderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_service.create_tender(db, data, user_id)
    return success(data=result, message="创建成功")


@router.get("/calendar", summary="日历数据")
async def get_calendar(
    year: int = Query(...),
    month: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await tender_service.get_calendar(db, year, month)
    return success(data=data)


@router.get("/stats", summary="统计概览")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await tender_service.get_stats(db)
    return success(data=data)


@router.get("/expiring", summary="到期提醒")
async def get_expiring(
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await tender_service.get_expiring(db)
    return success(data=data)


@router.get("/{tender_id}", summary="招标详情")
async def get_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await tender_service.get_tender(db, tender_id)
    return success(data=data)


@router.put("/{tender_id}", summary="更新招标信息")
async def update_tender(
    tender_id: int,
    data: TenderUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_service.update_tender(db, tender_id, data, user_id)
    return success(data=result, message="更新成功")


@router.delete("/{tender_id}", summary="删除招标信息")
async def delete_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await tender_service.delete_tender(db, tender_id, user_id)
    return success(message="删除成功")


@router.put("/{tender_id}/status", summary="更新跟进状态")
async def update_status(
    tender_id: int,
    data: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_service.update_status(db, tender_id, data.status, user_id)
    return success(data=result, message="状态更新成功")


@router.put("/{tender_id}/follower", summary="分配跟进人")
async def update_follower(
    tender_id: int,
    data: UpdateFollowerRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_service.update_follower(db, tender_id, data.follower_id, user_id)
    return success(data=result, message="跟进人分配成功")
