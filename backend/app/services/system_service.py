"""
系统管理服务 - 数据字典
"""

from typing import Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    BusinessException,
    DuplicateException,
    NotFoundException,
)
from app.common.pagination import PaginationParams, paginate
from app.models.system import SysDictItem, SysDictType, SysDepartment, SysUser
from app.schemas.system import (
    DictItemCreate,
    DictItemResponse,
    DictItemUpdate,
    DictTypeCreate,
    DictTypeResponse,
    DictTypeUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
)
from app.common.security import hash_password


class SystemService:

    # ------------------------------------------------------------------ #
    #  字典类型
    # ------------------------------------------------------------------ #

    async def list_dict_types(self, db: AsyncSession, params: PaginationParams) -> dict:
        query = select(SysDictType).where(SysDictType.is_deleted == 0)
        result = await paginate(db, query, params, sort_column=SysDictType.created_at)
        items = [DictTypeResponse.model_validate(obj).model_dump() for obj in result["items"]]
        return {**result, "items": items}

    async def create_dict_type(self, db: AsyncSession, data: DictTypeCreate, user_id: int) -> dict:
        # 检查 dict_code 唯一
        existing = await db.execute(
            select(SysDictType).where(
                SysDictType.dict_code == data.dict_code,
                SysDictType.is_deleted == 0,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateException(f"字典编码 '{data.dict_code}' 已存在")

        obj = SysDictType(
            dict_name=data.dict_name,
            dict_code=data.dict_code,
            description=data.description,
            status=data.status,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return DictTypeResponse.model_validate(obj).model_dump()

    async def update_dict_type(
        self, db: AsyncSession, dict_type_id: int, data: DictTypeUpdate, user_id: int
    ) -> dict:
        obj = await self._get_dict_type(db, dict_type_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.updated_by = user_id

        await db.commit()
        await db.refresh(obj)
        return DictTypeResponse.model_validate(obj).model_dump()

    async def delete_dict_type(self, db: AsyncSession, dict_type_id: int, user_id: int) -> None:
        obj = await self._get_dict_type(db, dict_type_id)

        # 检查是否有字典项
        items_result = await db.execute(
            select(SysDictItem).where(SysDictItem.dict_type_id == dict_type_id).limit(1)
        )
        if items_result.scalars().first():
            raise BusinessException("该字典类型下存在字典项，请先删除字典项")

        obj.is_deleted = 1
        obj.updated_by = user_id
        await db.commit()

    # ------------------------------------------------------------------ #
    #  字典项
    # ------------------------------------------------------------------ #

    async def list_dict_items(self, db: AsyncSession, dict_type_id: int) -> List[dict]:
        await self._get_dict_type(db, dict_type_id)

        result = await db.execute(
            select(SysDictItem)
            .where(SysDictItem.dict_type_id == dict_type_id)
            .order_by(SysDictItem.sort_order.asc(), SysDictItem.id.asc())
        )
        items = result.scalars().all()
        return [DictItemResponse.model_validate(item).model_dump() for item in items]

    async def create_dict_item(
        self, db: AsyncSession, dict_type_id: int, data: DictItemCreate, user_id: int
    ) -> dict:
        await self._get_dict_type(db, dict_type_id)

        # 检查 item_value 在同类型内唯一
        existing = await db.execute(
            select(SysDictItem).where(
                SysDictItem.dict_type_id == dict_type_id,
                SysDictItem.item_value == data.item_value,
            ).limit(1)
        )
        if existing.scalars().first():
            raise DuplicateException(f"字典值 '{data.item_value}' 在该类型下已存在")

        obj = SysDictItem(
            dict_type_id=dict_type_id,
            item_label=data.item_label,
            item_value=data.item_value,
            sort_order=data.sort_order,
            status=data.status,
            description=data.description,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return DictItemResponse.model_validate(obj).model_dump()

    async def update_dict_item(
        self, db: AsyncSession, item_id: int, data: DictItemUpdate, user_id: int
    ) -> dict:
        obj = await self._get_dict_item(db, item_id)

        update_data = data.model_dump(exclude_unset=True)

        # 如果改了 item_value，检查重复（排除自身）
        if "item_value" in update_data and update_data["item_value"] != obj.item_value:
            existing = await db.execute(
                select(SysDictItem).where(
                    SysDictItem.dict_type_id == obj.dict_type_id,
                    SysDictItem.item_value == update_data["item_value"],
                    SysDictItem.id != item_id,
                ).limit(1)
            )
            if existing.scalars().first():
                raise DuplicateException(f"字典值 '{update_data['item_value']}' 在该类型下已存在")

        for field, value in update_data.items():
            setattr(obj, field, value)

        await db.commit()
        await db.refresh(obj)
        return DictItemResponse.model_validate(obj).model_dump()

    async def delete_dict_item(self, db: AsyncSession, item_id: int, user_id: int) -> None:
        obj = await self._get_dict_item(db, item_id)
        await db.delete(obj)
        await db.commit()

    # ------------------------------------------------------------------ #
    #  按编码查字典
    # ------------------------------------------------------------------ #

    async def get_dict_by_code(self, db: AsyncSession, dict_code: str) -> List[dict]:
        result = await db.execute(
            select(SysDictItem)
            .join(SysDictType, SysDictType.id == SysDictItem.dict_type_id)
            .where(
                SysDictType.dict_code == dict_code,
                SysDictType.is_deleted == 0,
                SysDictType.status == 1,
                SysDictItem.status == 1,
            )
            .order_by(SysDictItem.sort_order.asc(), SysDictItem.id.asc())
        )
        items = result.scalars().all()
        return [DictItemResponse.model_validate(item).model_dump() for item in items]

    # ------------------------------------------------------------------ #
    #  私有辅助方法
    # ------------------------------------------------------------------ #

    async def _get_dict_type(self, db: AsyncSession, dict_type_id: int) -> SysDictType:
        result = await db.execute(
            select(SysDictType).where(
                SysDictType.id == dict_type_id,
                SysDictType.is_deleted == 0,
            )
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(f"字典类型 ID={dict_type_id} 不存在")
        return obj

    async def _get_dict_item(self, db: AsyncSession, item_id: int) -> SysDictItem:
        result = await db.execute(
            select(SysDictItem).where(SysDictItem.id == item_id)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(f"字典项 ID={item_id} 不存在")
        return obj


    # ================================================================== #
    #  部门管理
    # ================================================================== #

    async def get_department_tree(self, db: AsyncSession) -> list:
        result = await db.execute(
            select(SysDepartment)
            .where(SysDepartment.is_deleted == 0)
            .order_by(SysDepartment.sort_order.asc(), SysDepartment.id.asc())
        )
        depts = result.scalars().all()
        return self._build_tree(depts)

    def _build_tree(self, items: list) -> list:
        item_map: Dict[int, dict] = {}
        roots: list = []
        for item in items:
            d = DepartmentResponse.model_validate(item).model_dump()
            d["children"] = []
            item_map[item.id] = d
        for item in items:
            d = item_map[item.id]
            if item.parent_id is None or item.parent_id not in item_map:
                roots.append(d)
            else:
                item_map[item.parent_id]["children"].append(d)
        return roots

    async def get_department(self, db: AsyncSession, dept_id: int) -> dict:
        result = await db.execute(
            select(SysDepartment).where(SysDepartment.id == dept_id, SysDepartment.is_deleted == 0)
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise NotFoundException("部门不存在")
        return DepartmentResponse.model_validate(dept).model_dump()

    async def create_department(self, db: AsyncSession, data: DepartmentCreate, user_id: int) -> dict:
        existing = await db.execute(
            select(SysDepartment).where(SysDepartment.dept_code == data.dept_code, SysDepartment.is_deleted == 0)
        )
        if existing.scalar_one_or_none():
            raise DuplicateException(f"部门编码 '{data.dept_code}' 已存在")

        if data.parent_id is not None:
            parent = await db.execute(
                select(SysDepartment).where(SysDepartment.id == data.parent_id, SysDepartment.is_deleted == 0)
            )
            if parent.scalar_one_or_none() is None:
                raise BusinessException("上级部门不存在")

        dept = SysDepartment(**data.model_dump(), created_by=user_id, updated_by=user_id)
        db.add(dept)
        await db.flush()
        await db.refresh(dept)
        return DepartmentResponse.model_validate(dept).model_dump()

    async def update_department(self, db: AsyncSession, dept_id: int, data: DepartmentUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(SysDepartment).where(SysDepartment.id == dept_id, SysDepartment.is_deleted == 0)
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise NotFoundException("部门不存在")

        update_data = data.model_dump(exclude_unset=True)
        if "parent_id" in update_data and update_data["parent_id"] == dept_id:
            raise BusinessException("不能将自己设为上级部门")
        if "parent_id" in update_data and update_data["parent_id"] is not None:
            parent = await db.execute(
                select(SysDepartment).where(SysDepartment.id == update_data["parent_id"], SysDepartment.is_deleted == 0)
            )
            if parent.scalar_one_or_none() is None:
                raise BusinessException("上级部门不存在")

        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(dept, key, value)
        await db.flush()
        await db.refresh(dept)
        return DepartmentResponse.model_validate(dept).model_dump()

    async def delete_department(self, db: AsyncSession, dept_id: int, user_id: int) -> None:
        result = await db.execute(
            select(SysDepartment).where(SysDepartment.id == dept_id, SysDepartment.is_deleted == 0)
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise NotFoundException("部门不存在")

        children = await db.execute(
            select(SysDepartment).where(SysDepartment.parent_id == dept_id, SysDepartment.is_deleted == 0).limit(1)
        )
        if children.scalar_one_or_none():
            raise BusinessException("该部门下存在子部门，请先删除子部门")

        users = await db.execute(
            select(SysUser).where(SysUser.dept_id == dept_id, SysUser.is_deleted == 0).limit(1)
        )
        if users.scalar_one_or_none():
            raise BusinessException("该部门下存在用户，请先移除用户")

        dept.is_deleted = 1
        dept.updated_by = user_id
        await db.flush()

    # ================================================================== #
    #  用户管理
    # ================================================================== #

    async def list_users(self, db: AsyncSession, params: PaginationParams,
                         dept_id: Optional[int] = None, keyword: Optional[str] = None,
                         status: Optional[int] = None) -> dict:
        query = select(SysUser).where(SysUser.is_deleted == 0)
        if dept_id is not None:
            query = query.where(SysUser.dept_id == dept_id)
        if keyword:
            query = query.where(
                or_(SysUser.real_name.contains(keyword), SysUser.phone.contains(keyword))
            )
        if status is not None:
            query = query.where(SysUser.status == status)

        result = await paginate(db, query, params, sort_column=SysUser.id)
        items = []
        for user in result["items"]:
            user_dict = UserResponse.model_validate(user).model_dump()
            if user.dept_id:
                dept_result = await db.execute(
                    select(SysDepartment.dept_name).where(SysDepartment.id == user.dept_id)
                )
                dept_name = dept_result.scalar_one_or_none()
                user_dict["dept_name"] = dept_name
            items.append(user_dict)
        result["items"] = items
        return result

    async def create_user(self, db: AsyncSession, data: UserCreate, current_user_id: int) -> dict:
        existing = await db.execute(
            select(SysUser).where(SysUser.username == data.username, SysUser.is_deleted == 0)
        )
        if existing.scalar_one_or_none():
            raise DuplicateException(f"用户名 '{data.username}' 已存在")

        if data.dept_id is not None:
            dept = await db.execute(
                select(SysDepartment).where(SysDepartment.id == data.dept_id, SysDepartment.is_deleted == 0)
            )
            if dept.scalar_one_or_none() is None:
                raise BusinessException("部门不存在")

        user_data = data.model_dump(exclude={"password"})
        user_data["password_hash"] = hash_password(data.password)
        user_data["created_by"] = current_user_id
        user_data["updated_by"] = current_user_id
        user = SysUser(**user_data)
        db.add(user)
        await db.flush()
        await db.refresh(user)

        user_dict = UserResponse.model_validate(user).model_dump()
        if user.dept_id:
            dept_result = await db.execute(
                select(SysDepartment.dept_name).where(SysDepartment.id == user.dept_id)
            )
            user_dict["dept_name"] = dept_result.scalar_one_or_none()
        return user_dict

    async def update_user(self, db: AsyncSession, user_id: int, data: UserUpdate, current_user_id: int) -> dict:
        result = await db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundException("用户不存在")

        update_data = data.model_dump(exclude_unset=True)
        if "dept_id" in update_data and update_data["dept_id"] is not None:
            dept = await db.execute(
                select(SysDepartment).where(SysDepartment.id == update_data["dept_id"], SysDepartment.is_deleted == 0)
            )
            if dept.scalar_one_or_none() is None:
                raise BusinessException("部门不存在")

        update_data["updated_by"] = current_user_id
        for key, value in update_data.items():
            setattr(user, key, value)
        await db.flush()
        await db.refresh(user)

        user_dict = UserResponse.model_validate(user).model_dump()
        if user.dept_id:
            dept_result = await db.execute(
                select(SysDepartment.dept_name).where(SysDepartment.id == user.dept_id)
            )
            user_dict["dept_name"] = dept_result.scalar_one_or_none()
        return user_dict

    async def delete_user(self, db: AsyncSession, user_id: int, current_user_id: int) -> None:
        result = await db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundException("用户不存在")
        if user.id == current_user_id:
            raise BusinessException("不能删除自己")

        user.is_deleted = 1
        user.updated_by = current_user_id
        await db.flush()

    async def reset_password(self, db: AsyncSession, user_id: int, current_user_id: int) -> None:
        result = await db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundException("用户不存在")

        user.password_hash = hash_password("123456")
        user.updated_by = current_user_id
        await db.flush()


system_service = SystemService()
