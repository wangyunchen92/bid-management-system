"""
企业资料库服务
"""

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.library import Achievement, PersonnelCert, Product, Qualification
from app.schemas.library import (
    AchievementCreate,
    AchievementResponse,
    AchievementUpdate,
    PersonnelCertCreate,
    PersonnelCertResponse,
    PersonnelCertUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    QualificationCreate,
    QualificationResponse,
    QualificationUpdate,
)


class LibraryService:

    # ================================================================== #
    #  资质证书
    # ================================================================== #

    async def list_qualifications(
        self,
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
    ) -> dict:
        query = select(Qualification).where(Qualification.is_deleted == 0)
        if keyword:
            query = query.where(Qualification.cert_name.contains(keyword))
        result = await paginate(db, query, params, sort_column=Qualification.id)
        items = [QualificationResponse.model_validate(obj).model_dump() for obj in result["items"]]
        return {**result, "items": items}

    async def create_qualification(
        self,
        db: AsyncSession,
        data: QualificationCreate,
        user_id: int,
    ) -> dict:
        obj = Qualification(
            **data.model_dump(),
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return QualificationResponse.model_validate(obj).model_dump()

    async def update_qualification(
        self,
        db: AsyncSession,
        item_id: int,
        data: QualificationUpdate,
        user_id: int,
    ) -> dict:
        obj = await self._get_qualification(db, item_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.updated_by = user_id
        await db.commit()
        await db.refresh(obj)
        return QualificationResponse.model_validate(obj).model_dump()

    async def delete_qualification(
        self,
        db: AsyncSession,
        item_id: int,
        user_id: int,
    ) -> None:
        obj = await self._get_qualification(db, item_id)
        obj.is_deleted = 1
        obj.updated_by = user_id
        await db.commit()

    async def _get_qualification(self, db: AsyncSession, item_id: int) -> Qualification:
        result = await db.execute(
            select(Qualification).where(Qualification.id == item_id, Qualification.is_deleted == 0)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(f"资质证书 ID={item_id} 不存在")
        return obj

    # ================================================================== #
    #  业绩案例
    # ================================================================== #

    async def list_achievements(
        self,
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
    ) -> dict:
        query = select(Achievement).where(Achievement.is_deleted == 0)
        if keyword:
            query = query.where(Achievement.project_name.contains(keyword))
        result = await paginate(db, query, params, sort_column=Achievement.id)
        items = [AchievementResponse.model_validate(obj).model_dump() for obj in result["items"]]
        return {**result, "items": items}

    async def create_achievement(
        self,
        db: AsyncSession,
        data: AchievementCreate,
        user_id: int,
    ) -> dict:
        obj = Achievement(
            **data.model_dump(),
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return AchievementResponse.model_validate(obj).model_dump()

    async def update_achievement(
        self,
        db: AsyncSession,
        item_id: int,
        data: AchievementUpdate,
        user_id: int,
    ) -> dict:
        obj = await self._get_achievement(db, item_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.updated_by = user_id
        await db.commit()
        await db.refresh(obj)
        return AchievementResponse.model_validate(obj).model_dump()

    async def delete_achievement(
        self,
        db: AsyncSession,
        item_id: int,
        user_id: int,
    ) -> None:
        obj = await self._get_achievement(db, item_id)
        obj.is_deleted = 1
        obj.updated_by = user_id
        await db.commit()

    async def _get_achievement(self, db: AsyncSession, item_id: int) -> Achievement:
        result = await db.execute(
            select(Achievement).where(Achievement.id == item_id, Achievement.is_deleted == 0)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(f"业绩案例 ID={item_id} 不存在")
        return obj

    # ================================================================== #
    #  人员证书
    # ================================================================== #

    async def list_personnel_certs(
        self,
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
    ) -> dict:
        query = select(PersonnelCert).where(PersonnelCert.is_deleted == 0)
        if keyword:
            query = query.where(
                or_(
                    PersonnelCert.person_name.contains(keyword),
                    PersonnelCert.cert_name.contains(keyword),
                )
            )
        result = await paginate(db, query, params, sort_column=PersonnelCert.id)
        items = [PersonnelCertResponse.model_validate(obj).model_dump() for obj in result["items"]]
        return {**result, "items": items}

    async def create_personnel_cert(
        self,
        db: AsyncSession,
        data: PersonnelCertCreate,
        user_id: int,
    ) -> dict:
        obj = PersonnelCert(
            **data.model_dump(),
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return PersonnelCertResponse.model_validate(obj).model_dump()

    async def update_personnel_cert(
        self,
        db: AsyncSession,
        item_id: int,
        data: PersonnelCertUpdate,
        user_id: int,
    ) -> dict:
        obj = await self._get_personnel_cert(db, item_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.updated_by = user_id
        await db.commit()
        await db.refresh(obj)
        return PersonnelCertResponse.model_validate(obj).model_dump()

    async def delete_personnel_cert(
        self,
        db: AsyncSession,
        item_id: int,
        user_id: int,
    ) -> None:
        obj = await self._get_personnel_cert(db, item_id)
        obj.is_deleted = 1
        obj.updated_by = user_id
        await db.commit()

    async def _get_personnel_cert(self, db: AsyncSession, item_id: int) -> PersonnelCert:
        result = await db.execute(
            select(PersonnelCert).where(PersonnelCert.id == item_id, PersonnelCert.is_deleted == 0)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(f"人员证书 ID={item_id} 不存在")
        return obj

    # ================================================================== #
    #  产品/设备
    # ================================================================== #

    async def list_products(
        self,
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
    ) -> dict:
        query = select(Product).where(Product.is_deleted == 0)
        if keyword:
            query = query.where(Product.name.contains(keyword))
        result = await paginate(db, query, params, sort_column=Product.id)
        items = [ProductResponse.model_validate(obj).model_dump() for obj in result["items"]]
        return {**result, "items": items}

    async def create_product(
        self,
        db: AsyncSession,
        data: ProductCreate,
        user_id: int,
    ) -> dict:
        obj = Product(
            **data.model_dump(),
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return ProductResponse.model_validate(obj).model_dump()

    async def update_product(
        self,
        db: AsyncSession,
        item_id: int,
        data: ProductUpdate,
        user_id: int,
    ) -> dict:
        obj = await self._get_product(db, item_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.updated_by = user_id
        await db.commit()
        await db.refresh(obj)
        return ProductResponse.model_validate(obj).model_dump()

    async def delete_product(
        self,
        db: AsyncSession,
        item_id: int,
        user_id: int,
    ) -> None:
        obj = await self._get_product(db, item_id)
        obj.is_deleted = 1
        obj.updated_by = user_id
        await db.commit()

    async def _get_product(self, db: AsyncSession, item_id: int) -> Product:
        result = await db.execute(
            select(Product).where(Product.id == item_id, Product.is_deleted == 0)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(f"产品/设备 ID={item_id} 不存在")
        return obj


library_service = LibraryService()
