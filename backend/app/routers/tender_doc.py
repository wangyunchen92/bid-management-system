"""
招标文件解析路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_user_id, get_db
from app.common.response import success
from app.services.tender_doc_service import tender_doc_service

router = APIRouter()


@router.post("/upload", summary="上传并解析招标文件")
async def upload_and_parse(
    file: UploadFile = File(...),
    project_id: Optional[int] = Query(default=None),
    tender_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await tender_doc_service.upload_and_parse(
        db, file, user_id, project_id=project_id, tender_id=tender_id,
    )
    return success(data=result, message="文件解析完成" if result.get("parse_status") == "COMPLETED" else "文件解析失败")


@router.get("/{doc_id}", summary="获取文档详情")
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await tender_doc_service.get_document(db, doc_id)
    return success(data=result)


@router.get("/by-project/{project_id}", summary="按项目查文档")
async def list_by_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await tender_doc_service.list_by_project(db, project_id)
    return success(data=result)


@router.get("/by-tender/{tender_id}", summary="按招标查文档")
async def list_by_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await tender_doc_service.list_by_tender(db, tender_id)
    return success(data=result)


@router.delete("/{doc_id}", summary="删除文档")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await tender_doc_service.delete_document(db, doc_id, user_id)
    return success(message="删除成功")
