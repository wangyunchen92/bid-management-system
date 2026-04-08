"""
审批路由 /api/v1/approval/*
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.approval import SubmitApprovalRequest, ApproveRequest, RejectRequest, TransferRequest
from app.services.approval_service import approval_service

router = APIRouter()


@router.post("/submit", summary="发起审批")
async def submit_approval(
    data: SubmitApprovalRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.submit(
        db, title=data.title, biz_type=data.biz_type,
        biz_id=data.biz_id, approver_id=data.approver_id,
        initiator_id=user_id,
    )
    return success(data=result, message="审批已发起")


@router.get("/my-pending", summary="我的待审批")
async def my_pending(
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.my_pending(db, user_id, params)
    return page_response(
        items=result["items"], total=result["total"],
        page=result["page"], page_size=result["page_size"],
    )


@router.get("/my-initiated", summary="我发起的审批")
async def my_initiated(
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.my_initiated(db, user_id, params)
    return page_response(
        items=result["items"], total=result["total"],
        page=result["page"], page_size=result["page_size"],
    )


@router.get("/{instance_id}", summary="审批详情")
async def get_detail(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.get_detail(db, instance_id, user_id)
    return success(data=result)


@router.post("/{instance_id}/approve", summary="同意")
async def approve(
    instance_id: int,
    data: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.approve(db, instance_id, user_id, data.comment)
    return success(data=result, message="已同意")


@router.post("/{instance_id}/reject", summary="驳回")
async def reject(
    instance_id: int,
    data: RejectRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.reject(db, instance_id, user_id, data.comment)
    return success(data=result, message="已驳回")


@router.post("/{instance_id}/transfer", summary="转审")
async def transfer(
    instance_id: int,
    data: TransferRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await approval_service.transfer(db, instance_id, user_id, data.to_user_id, data.comment)
    return success(data=result, message="已转审")
