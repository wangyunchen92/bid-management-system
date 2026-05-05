"""
标书编制服务
"""

from typing import List, Optional

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException, BusinessException
from app.common.pagination import PaginationParams, paginate
from app.models.bid import BidProject, BidSection
from app.models.tender import Tender
from app.models.system import SysUser
from app.schemas.bid import BidProjectCreate, BidProjectUpdate, BidProjectResponse, BidSectionCreate, BidSectionUpdate, BidSectionResponse


class BidService:

    # =========== 辅助方法 ===========

    async def _get_user_name(self, db: AsyncSession, user_id: Optional[int]) -> Optional[str]:
        if not user_id:
            return None
        result = await db.execute(select(SysUser.real_name).where(SysUser.id == user_id))
        return result.scalar_one_or_none()

    async def _get_tender_title(self, db: AsyncSession, tender_id: Optional[int]) -> Optional[str]:
        if not tender_id:
            return None
        result = await db.execute(select(Tender.title).where(Tender.id == tender_id, Tender.is_deleted == 0))
        return result.scalar_one_or_none()

    async def _get_section_count(self, db: AsyncSession, project_id: int) -> int:
        result = await db.execute(
            select(func.count(BidSection.id)).where(
                BidSection.project_id == project_id,
                BidSection.is_deleted == 0,
            )
        )
        return result.scalar() or 0

    async def _project_to_dict(self, db: AsyncSession, project: BidProject) -> dict:
        d = BidProjectResponse.model_validate(project).model_dump()
        d["tender_title"] = await self._get_tender_title(db, project.tender_id)
        d["leader_name"] = await self._get_user_name(db, project.leader_id)
        d["section_count"] = await self._get_section_count(db, project.id)
        return d

    async def _section_to_dict(self, db: AsyncSession, section: BidSection) -> dict:
        d = BidSectionResponse.model_validate(section).model_dump()
        d["assignee_name"] = await self._get_user_name(db, section.assignee_id)
        d["children"] = []
        return d

    def _build_tree(self, sections: list, parent_id: Optional[int] = None) -> list:
        """内存构建章节树"""
        tree = []
        for s in sections:
            if s["parent_id"] == parent_id:
                s["children"] = self._build_tree(sections, s["id"])
                tree.append(s)
        tree.sort(key=lambda x: x.get("sort_order", 0))
        return tree

    # =========== 标书项目 ===========

    async def list_projects(
        self,
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        leader_id: Optional[int] = None,
    ) -> dict:
        query = select(BidProject).where(BidProject.is_deleted == 0)

        if keyword:
            query = query.where(BidProject.title.contains(keyword))
        if status:
            query = query.where(BidProject.status == status)
        if leader_id:
            query = query.where(BidProject.leader_id == leader_id)

        result = await paginate(db, query, params, sort_column=BidProject.id)
        items = []
        for p in result["items"]:
            items.append(await self._project_to_dict(db, p))
        result["items"] = items
        return result

    async def create_project(self, db: AsyncSession, data: BidProjectCreate, user_id: int) -> dict:
        project = BidProject(**data.model_dump(), created_by=user_id, updated_by=user_id)
        db.add(project)
        await db.flush()
        await db.refresh(project)
        return await self._project_to_dict(db, project)

    async def get_project(self, db: AsyncSession, project_id: int) -> dict:
        result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundException("标书项目不存在")
        return await self._project_to_dict(db, project)

    async def update_project(self, db: AsyncSession, project_id: int, data: BidProjectUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundException("标书项目不存在")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(project, key, value)
        await db.flush()
        await db.refresh(project)
        return await self._project_to_dict(db, project)

    async def delete_project(self, db: AsyncSession, project_id: int, user_id: int) -> None:
        result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundException("标书项目不存在")

        # 同时逻辑删除所有章节
        sections_result = await db.execute(
            select(BidSection).where(BidSection.project_id == project_id, BidSection.is_deleted == 0)
        )
        for section in sections_result.scalars().all():
            section.is_deleted = 1
            section.updated_by = user_id

        project.is_deleted = 1
        project.updated_by = user_id
        await db.flush()

    async def get_by_tender(self, db: AsyncSession, tender_id: int) -> list:
        result = await db.execute(
            select(BidProject).where(
                BidProject.tender_id == tender_id,
                BidProject.is_deleted == 0,
            ).order_by(BidProject.id.desc())
        )
        projects = result.scalars().all()
        items = []
        for p in projects:
            items.append(await self._project_to_dict(db, p))
        return items

    # =========== 标书章节 ===========

    async def get_section_tree(self, db: AsyncSession, project_id: int) -> list:
        # 验证项目存在
        proj_result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        if proj_result.scalar_one_or_none() is None:
            raise NotFoundException("标书项目不存在")

        result = await db.execute(
            select(BidSection).where(
                BidSection.project_id == project_id,
                BidSection.is_deleted == 0,
            ).order_by(BidSection.sort_order.asc(), BidSection.id.asc())
        )
        sections = result.scalars().all()

        flat = []
        for s in sections:
            d = await self._section_to_dict(db, s)
            flat.append(d)

        return self._build_tree(flat, parent_id=None)

    async def create_section(self, db: AsyncSession, data: BidSectionCreate, user_id: int) -> dict:
        # 验证项目存在
        proj_result = await db.execute(
            select(BidProject).where(BidProject.id == data.project_id, BidProject.is_deleted == 0)
        )
        if proj_result.scalar_one_or_none() is None:
            raise NotFoundException("标书项目不存在")

        section_data = data.model_dump()
        # 计算 word_count
        content = section_data.get("content")
        section_data["word_count"] = len(content) if content else 0

        section = BidSection(**section_data, created_by=user_id, updated_by=user_id)
        db.add(section)
        await db.flush()
        await db.refresh(section)
        return await self._section_to_dict(db, section)

    async def get_section(self, db: AsyncSession, section_id: int) -> dict:
        result = await db.execute(
            select(BidSection).where(BidSection.id == section_id, BidSection.is_deleted == 0)
        )
        section = result.scalar_one_or_none()
        if section is None:
            raise NotFoundException("章节不存在")
        return await self._section_to_dict(db, section)

    async def update_section(self, db: AsyncSession, section_id: int, data: BidSectionUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(BidSection).where(BidSection.id == section_id, BidSection.is_deleted == 0)
        )
        section = result.scalar_one_or_none()
        if section is None:
            raise NotFoundException("章节不存在")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id

        # 自动计算 word_count
        if "content" in update_data:
            content = update_data["content"]
            update_data["word_count"] = len(content) if content else 0

        for key, value in update_data.items():
            setattr(section, key, value)
        await db.flush()
        await db.refresh(section)
        return await self._section_to_dict(db, section)

    async def delete_section(self, db: AsyncSession, section_id: int, user_id: int) -> None:
        result = await db.execute(
            select(BidSection).where(BidSection.id == section_id, BidSection.is_deleted == 0)
        )
        section = result.scalar_one_or_none()
        if section is None:
            raise NotFoundException("章节不存在")

        # 递归删除子章节
        await self._delete_children(db, section_id, user_id)
        section.is_deleted = 1
        section.updated_by = user_id
        await db.flush()

    async def _delete_children(self, db: AsyncSession, parent_id: int, user_id: int) -> None:
        result = await db.execute(
            select(BidSection).where(BidSection.parent_id == parent_id, BidSection.is_deleted == 0)
        )
        children = result.scalars().all()
        for child in children:
            await self._delete_children(db, child.id, user_id)
            child.is_deleted = 1
            child.updated_by = user_id

    async def reorder_sections(self, db: AsyncSession, project_id: int, items: list, user_id: int) -> list:
        """批量更新章节的 parent_id + sort_order。

        items: [{id: int, parent_id: Optional[int], sort_order: int}]
        """
        proj_result = await db.execute(
            select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == 0)
        )
        if proj_result.scalar_one_or_none() is None:
            raise NotFoundException("标书项目不存在")

        for item in items:
            sid = item.id if hasattr(item, "id") else item["id"]
            new_parent = item.parent_id if hasattr(item, "parent_id") else item.get("parent_id")
            new_order = item.sort_order if hasattr(item, "sort_order") else item.get("sort_order", 0)

            result = await db.execute(
                select(BidSection).where(
                    BidSection.id == sid,
                    BidSection.project_id == project_id,
                    BidSection.is_deleted == 0,
                )
            )
            section = result.scalar_one_or_none()
            if section is None:
                continue
            section.parent_id = new_parent
            section.sort_order = new_order
            section.updated_by = user_id

        await db.flush()
        return await self.get_section_tree(db, project_id)


bid_service = BidService()
