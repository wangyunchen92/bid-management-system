"""
系统管理路由 - 数据字典
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_user_id, get_db, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import page_response, success
from app.schemas.system import DictItemCreate, DictItemUpdate, DictTypeCreate, DictTypeUpdate
from app.services.system_service import system_service

router = APIRouter()


# ------------------------------------------------------------------ #
#  字典类型
# ------------------------------------------------------------------ #

@router.get("/dict-types")
async def list_dict_types(
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await system_service.list_dict_types(db, params)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/dict-types")
async def create_dict_type(
    data: DictTypeCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await system_service.create_dict_type(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/dict-types/{dict_type_id}")
async def update_dict_type(
    dict_type_id: int,
    data: DictTypeUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await system_service.update_dict_type(db, dict_type_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/dict-types/{dict_type_id}")
async def delete_dict_type(
    dict_type_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.delete_dict_type(db, dict_type_id, user_id)
    return success(message="删除成功")


# ------------------------------------------------------------------ #
#  字典项
# ------------------------------------------------------------------ #

@router.get("/dict-types/{dict_type_id}/items")
async def list_dict_items(
    dict_type_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    items = await system_service.list_dict_items(db, dict_type_id)
    return success(data=items)


@router.post("/dict-types/{dict_type_id}/items")
async def create_dict_item(
    dict_type_id: int,
    data: DictItemCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await system_service.create_dict_item(db, dict_type_id, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/dict-items/{item_id}")
async def update_dict_item(
    item_id: int,
    data: DictItemUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await system_service.update_dict_item(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/dict-items/{item_id}")
async def delete_dict_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.delete_dict_item(db, item_id, user_id)
    return success(message="删除成功")


# ------------------------------------------------------------------ #
#  按编码查字典
# ------------------------------------------------------------------ #

@router.get("/dicts/{dict_code}")
async def get_dict_by_code(
    dict_code: str,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    items = await system_service.get_dict_by_code(db, dict_code)
    return success(data=items)
