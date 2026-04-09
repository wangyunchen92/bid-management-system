"""
标书知识库服务
"""

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.knowledge import KnowledgeTemplate
from app.schemas.knowledge import KnowledgeTemplateCreate, KnowledgeTemplateUpdate, KnowledgeTemplateResponse


class KnowledgeService:

    def _to_dict(self, obj: KnowledgeTemplate) -> dict:
        return KnowledgeTemplateResponse.model_validate(obj).model_dump()

    async def list_templates(
        self,
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        query = select(KnowledgeTemplate).where(KnowledgeTemplate.is_deleted == 0)

        if keyword:
            query = query.where(
                or_(
                    KnowledgeTemplate.title.contains(keyword),
                    KnowledgeTemplate.tags.contains(keyword),
                    KnowledgeTemplate.content.contains(keyword),
                )
            )
        if category:
            query = query.where(KnowledgeTemplate.category == category)

        result = await paginate(db, query, params, sort_column=KnowledgeTemplate.id)
        result["items"] = [self._to_dict(t) for t in result["items"]]
        return result

    async def create_template(
        self,
        db: AsyncSession,
        data: KnowledgeTemplateCreate,
        user_id: int,
    ) -> dict:
        obj = KnowledgeTemplate(**data.model_dump(), created_by=user_id, updated_by=user_id)
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return self._to_dict(obj)

    async def get_template(self, db: AsyncSession, template_id: int) -> dict:
        result = await db.execute(
            select(KnowledgeTemplate).where(
                KnowledgeTemplate.id == template_id,
                KnowledgeTemplate.is_deleted == 0,
            )
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException("知识库模板不存在")
        return self._to_dict(obj)

    async def update_template(
        self,
        db: AsyncSession,
        template_id: int,
        data: KnowledgeTemplateUpdate,
        user_id: int,
    ) -> dict:
        result = await db.execute(
            select(KnowledgeTemplate).where(
                KnowledgeTemplate.id == template_id,
                KnowledgeTemplate.is_deleted == 0,
            )
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException("知识库模板不存在")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(obj, key, value)
        await db.flush()
        await db.refresh(obj)
        return self._to_dict(obj)

    async def delete_template(self, db: AsyncSession, template_id: int, user_id: int) -> None:
        result = await db.execute(
            select(KnowledgeTemplate).where(
                KnowledgeTemplate.id == template_id,
                KnowledgeTemplate.is_deleted == 0,
            )
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException("知识库模板不存在")
        obj.is_deleted = 1
        obj.updated_by = user_id
        await db.flush()

    async def search_templates(
        self,
        db: AsyncSession,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        query = select(KnowledgeTemplate).where(KnowledgeTemplate.is_deleted == 0)

        if keyword:
            query = query.where(
                or_(
                    KnowledgeTemplate.title.contains(keyword),
                    KnowledgeTemplate.tags.contains(keyword),
                    KnowledgeTemplate.content.contains(keyword),
                )
            )
        if category:
            query = query.where(KnowledgeTemplate.category == category)

        query = query.order_by(KnowledgeTemplate.usage_count.desc()).limit(limit)
        result = await db.execute(query)
        return [self._to_dict(t) for t in result.scalars().all()]

    async def increment_usage(self, db: AsyncSession, template_id: int) -> None:
        result = await db.execute(
            select(KnowledgeTemplate).where(
                KnowledgeTemplate.id == template_id,
                KnowledgeTemplate.is_deleted == 0,
            )
        )
        obj = result.scalar_one_or_none()
        if obj:
            obj.usage_count = (obj.usage_count or 0) + 1
            await db.flush()


knowledge_service = KnowledgeService()
