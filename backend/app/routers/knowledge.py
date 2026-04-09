"""
标书知识库路由 /api/v1/knowledge/*
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import success, page_response
from app.schemas.knowledge import KnowledgeTemplateCreate, KnowledgeTemplateUpdate
from app.services.knowledge_service import knowledge_service

router = APIRouter()


@router.get("/list", summary="知识库模板列表")
async def list_templates(
    params: PaginationParams = Depends(get_pagination_params),
    keyword: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await knowledge_service.list_templates(db, params, keyword=keyword, category=category)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/search", summary="搜索知识库模板")
async def search_templates(
    keyword: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    items = await knowledge_service.search_templates(db, keyword=keyword, category=category, limit=limit)
    return success(data=items)


@router.post("", summary="创建知识库模板")
async def create_template(
    data: KnowledgeTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await knowledge_service.create_template(db, data, user_id)
    return success(data=result, message="创建成功")


@router.get("/{template_id}", summary="知识库模板详情")
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await knowledge_service.get_template(db, template_id)
    return success(data=result)


@router.put("/{template_id}", summary="更新知识库模板")
async def update_template(
    template_id: int,
    data: KnowledgeTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await knowledge_service.update_template(db, template_id, data, user_id)
    return success(data=result, message="更新成功")


@router.delete("/{template_id}", summary="删除知识库模板")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await knowledge_service.delete_template(db, template_id, user_id)
    return success(message="删除成功")
