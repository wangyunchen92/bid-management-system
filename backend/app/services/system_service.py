"""
系统管理服务 - 数据字典
"""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    BusinessException,
    DuplicateException,
    NotFoundException,
)
from app.common.pagination import PaginationParams, paginate
from app.models.system import SysDictItem, SysDictType
from app.schemas.system import (
    DictItemCreate,
    DictItemResponse,
    DictItemUpdate,
    DictTypeCreate,
    DictTypeResponse,
    DictTypeUpdate,
)


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
            select(SysDictItem).where(SysDictItem.dict_type_id == dict_type_id)
        )
        if items_result.scalar_one_or_none():
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
            )
        )
        if existing.scalar_one_or_none():
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
                )
            )
            if existing.scalar_one_or_none():
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


system_service = SystemService()
