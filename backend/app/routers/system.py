"""
系统管理路由 - 数据字典
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_user_id, get_db, require_super_admin
from app.common.pagination import PaginationParams, get_pagination_params
from app.common.response import page_response, success
from app.schemas.system import (
    DictItemCreate, DictItemUpdate, DictTypeCreate, DictTypeUpdate,
    DepartmentCreate, DepartmentUpdate,
    UserCreate, UserUpdate,
    RoleCreate, RoleUpdate, AssignRolesRequest,
)
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


# ================================================================== #
#  部门管理
# ================================================================== #

@router.get("/departments/tree", summary="部门树")
async def get_department_tree(
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await system_service.get_department_tree(db)
    return success(data=data)


@router.post("/departments", summary="创建部门")
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    dept = await system_service.create_department(db, data, user_id)
    return success(data=dept, message="创建成功")


@router.get("/departments/{dept_id}", summary="部门详情")
async def get_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await system_service.get_department(db, dept_id)
    return success(data=data)


@router.put("/departments/{dept_id}", summary="更新部门")
async def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    dept = await system_service.update_department(db, dept_id, data, user_id)
    return success(data=dept, message="更新成功")


@router.delete("/departments/{dept_id}", summary="删除部门")
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.delete_department(db, dept_id, user_id)
    return success(message="删除成功")


# ================================================================== #
#  用户管理
# ================================================================== #

@router.get("/users", summary="用户列表")
async def list_users(
    params: PaginationParams = Depends(get_pagination_params),
    dept_id: Optional[int] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    status: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    result = await system_service.list_users(db, params, dept_id=dept_id, keyword=keyword, status=status)
    return page_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/users", summary="创建用户")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    user = await system_service.create_user(db, data, user_id)
    return success(data=user, message="创建成功")


@router.put("/users/{target_user_id}", summary="更新用户")
async def update_user(
    target_user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    user = await system_service.update_user(db, target_user_id, data, user_id)
    return success(data=user, message="更新成功")


@router.delete("/users/{target_user_id}", summary="删除用户")
async def delete_user(
    target_user_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.delete_user(db, target_user_id, user_id)
    return success(message="删除成功")


@router.put("/users/{target_user_id}/reset-password", summary="重置密码")
async def reset_password(
    target_user_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.reset_password(db, target_user_id, user_id)
    return success(message="密码已重置为 123456")


# ================================================================== #
#  角色管理
# ================================================================== #

@router.get("/roles", summary="角色列表")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await system_service.list_roles(db)
    return success(data=data)


@router.post("/roles", summary="创建角色")
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    role = await system_service.create_role(db, data, user_id)
    return success(data=role, message="创建成功")


@router.put("/roles/{role_id}", summary="更新角色")
async def update_role(
    role_id: int,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    role = await system_service.update_role(db, role_id, data, user_id)
    return success(data=role, message="更新成功")


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    await system_service.delete_role(db, role_id, user_id)
    return success(message="删除成功")


@router.get("/users/{target_user_id}/roles", summary="获取用户角色")
async def get_user_roles(
    target_user_id: int,
    db: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_user_id),
):
    data = await system_service.get_user_roles(db, target_user_id)
    return success(data=data)


@router.put("/users/{target_user_id}/roles", summary="分配用户角色")
async def assign_user_roles(
    target_user_id: int,
    data: AssignRolesRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(require_super_admin),
):
    roles = await system_service.assign_user_roles(db, target_user_id, data.role_ids, user_id)
    return success(data=roles, message="角色分配成功")
