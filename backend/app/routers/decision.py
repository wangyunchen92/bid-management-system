"""
投标决策路由 /api/v1/decision/*
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.decision import DecisionCreate, DecisionUpdate
from app.services.decision_service import decision_service

router = APIRouter()


@router.get("/list", summary="投标决策列表")
async def list_decisions(
    params: PaginationParams = Depends(get_pagination_params),
    keyword: Optional[str] = Query(default=None, description="招标标题关键词"),
    decision_result: Optional[str] = Query(default=None, description="决策结果筛选"),
    initiator_id: Optional[int] = Query(default=None, description="发起人筛选"),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await decision_service.list_decisions(
        db, params, keyword=keyword, decision_result=decision_result, initiator_id=initiator_id,
    )
    return page_response(items=result["items"], total=result["total"], page=result["page"], page_size=result["page_size"])


@router.post("", summary="创建投标决策（含审批）")
async def create_decision(
    data: DecisionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await decision_service.create_decision(db, data, user_id)
    return success(data=result, message="创建成功")


@router.get("/by-tender/{tender_id}", summary="按招标查询决策列表")
async def get_by_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    items = await decision_service.get_by_tender(db, tender_id)
    return success(data=items)


@router.get("/{decision_id}", summary="投标决策详情")
async def get_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await decision_service.get_decision(db, decision_id)
    return success(data=data)


@router.put("/{decision_id}", summary="更新投标决策")
async def update_decision(
    decision_id: int,
    data: DecisionUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await decision_service.update_decision(db, decision_id, data, user_id)
    return success(data=result, message="更新成功")


@router.delete("/{decision_id}", summary="删除投标决策（超管）")
async def delete_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await decision_service.delete_decision(db, decision_id, user_id)
    return success(message="删除成功")
