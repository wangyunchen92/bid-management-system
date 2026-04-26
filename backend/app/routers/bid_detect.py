"""标书检测路由 /api/v1/bid/"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id
from app.common.response import success
from app.services.bid_detect_service import bid_detect_service

router = APIRouter()


@router.post("/projects/{project_id}/detect", summary="标书检测（SSE流式）")
async def detect_bid(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """执行标书检测：规则预检 + AI逐类检测，SSE 流式推送进度"""
    async def event_generator():
        async for event in bid_detect_service.run_detection_stream(db, project_id, user_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/projects/{project_id}/detect/reports", summary="检测报告列表")
async def list_reports(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    reports = await bid_detect_service.get_reports(db, project_id)
    return success(data=reports)


@router.get("/projects/{project_id}/detect/reports/{report_id}", summary="检测报告详情")
async def get_report(
    project_id: int,
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    report = await bid_detect_service.get_report_detail(db, report_id)
    if not report:
        raise Exception("检测报告不存在")
    return success(data=report)
