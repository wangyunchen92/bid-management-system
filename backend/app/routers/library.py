"""
企业资料库路由
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_user_id, get_db, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import page_response, success
from app.schemas.library import (
    AchievementCreate,
    AchievementUpdate,
    PersonnelCertCreate,
    PersonnelCertUpdate,
    ProductCreate,
    ProductUpdate,
    QualificationCreate,
    QualificationUpdate,
)
from app.services.library_service import library_service

router = APIRouter()


# ================================================================== #
#  资质证书
# ================================================================== #

@router.get("/qualifications")
async def list_qualifications(
    keyword: Optional[str] = Query(default=None),
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await library_service.list_qualifications(db, params, keyword=keyword)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/qualifications")
async def create_qualification(
    data: QualificationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.create_qualification(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/qualifications/{item_id}")
async def update_qualification(
    item_id: int,
    data: QualificationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.update_qualification(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/qualifications/{item_id}")
async def delete_qualification(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await library_service.delete_qualification(db, item_id, user_id)
    return success(message="删除成功")


# ================================================================== #
#  业绩案例
# ================================================================== #

@router.get("/achievements")
async def list_achievements(
    keyword: Optional[str] = Query(default=None),
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await library_service.list_achievements(db, params, keyword=keyword)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/achievements")
async def create_achievement(
    data: AchievementCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.create_achievement(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/achievements/{item_id}")
async def update_achievement(
    item_id: int,
    data: AchievementUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.update_achievement(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/achievements/{item_id}")
async def delete_achievement(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await library_service.delete_achievement(db, item_id, user_id)
    return success(message="删除成功")


# ================================================================== #
#  人员证书
# ================================================================== #

@router.get("/personnel-certs")
async def list_personnel_certs(
    keyword: Optional[str] = Query(default=None),
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await library_service.list_personnel_certs(db, params, keyword=keyword)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/personnel-certs")
async def create_personnel_cert(
    data: PersonnelCertCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.create_personnel_cert(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/personnel-certs/{item_id}")
async def update_personnel_cert(
    item_id: int,
    data: PersonnelCertUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.update_personnel_cert(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/personnel-certs/{item_id}")
async def delete_personnel_cert(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await library_service.delete_personnel_cert(db, item_id, user_id)
    return success(message="删除成功")


# ================================================================== #
#  产品/设备
# ================================================================== #

@router.get("/products")
async def list_products(
    keyword: Optional[str] = Query(default=None),
    params: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await library_service.list_products(db, params, keyword=keyword)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/products")
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.create_product(db, data, user_id)
    return success(data=item, message="创建成功")


@router.put("/products/{item_id}")
async def update_product(
    item_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    item = await library_service.update_product(db, item_id, data, user_id)
    return success(data=item, message="更新成功")


@router.delete("/products/{item_id}")
async def delete_product(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await library_service.delete_product(db, item_id, user_id)
    return success(message="删除成功")
