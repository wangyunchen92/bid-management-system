"""
开标跟踪服务
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.opening import BidOpening
from app.models.tender import Tender
from app.schemas.opening import OpeningCreate, OpeningUpdate, OpeningResponse


class OpeningService:

    def _to_dict(self, opening: BidOpening, tender_title: Optional[str] = None, tender_no: Optional[str] = None) -> dict:
        d = OpeningResponse.model_validate(opening).model_dump()
        d["tender_title"] = tender_title
        d["tender_no"] = tender_no
        # Decimal -> float
        for field in ("our_price", "win_price"):
            if d.get(field) is not None:
                d[field] = float(d[field])
        return d

    async def _get_tender(self, db: AsyncSession, tender_id: int) -> Tender:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("关联招标信息不存在")
        return tender

    async def create_opening(self, db: AsyncSession, data: OpeningCreate, user_id: int) -> dict:
        tender = await self._get_tender(db, data.tender_id)

        opening = BidOpening(
            **data.model_dump(),
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(opening)

        # 更新招标状态为已开标
        tender.status = "OPENED"
        tender.updated_by = user_id

        await db.flush()
        await db.refresh(opening)
        return self._to_dict(opening, tender_title=tender.title, tender_no=tender.tender_no)

    async def list_openings(
        self,
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
        result: Optional[str] = None,
    ) -> dict:
        query = select(BidOpening).where(BidOpening.is_deleted == 0)

        # 按关键词（招标标题）筛选需要 JOIN
        if keyword:
            query = query.join(Tender, BidOpening.tender_id == Tender.id).where(
                Tender.title.contains(keyword)
            )

        if result:
            query = query.where(BidOpening.result == result)

        paginated = await paginate(db, query, params, sort_column=BidOpening.id)

        items = []
        for opening in paginated["items"]:
            # 获取关联招标信息
            tender_result = await db.execute(
                select(Tender.title, Tender.tender_no).where(Tender.id == opening.tender_id)
            )
            row = tender_result.first()
            tender_title = row[0] if row else None
            tender_no = row[1] if row else None
            items.append(self._to_dict(opening, tender_title=tender_title, tender_no=tender_no))

        paginated["items"] = items
        return paginated

    async def get_opening(self, db: AsyncSession, opening_id: int) -> dict:
        result = await db.execute(
            select(BidOpening).where(BidOpening.id == opening_id, BidOpening.is_deleted == 0)
        )
        opening = result.scalar_one_or_none()
        if opening is None:
            raise NotFoundException("开标记录不存在")

        tender_result = await db.execute(
            select(Tender.title, Tender.tender_no).where(Tender.id == opening.tender_id)
        )
        row = tender_result.first()
        return self._to_dict(opening, tender_title=row[0] if row else None, tender_no=row[1] if row else None)

    async def update_opening(self, db: AsyncSession, opening_id: int, data: OpeningUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(BidOpening).where(BidOpening.id == opening_id, BidOpening.is_deleted == 0)
        )
        opening = result.scalar_one_or_none()
        if opening is None:
            raise NotFoundException("开标记录不存在")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(opening, key, value)

        await db.flush()
        await db.refresh(opening)

        tender_result = await db.execute(
            select(Tender.title, Tender.tender_no).where(Tender.id == opening.tender_id)
        )
        row = tender_result.first()
        return self._to_dict(opening, tender_title=row[0] if row else None, tender_no=row[1] if row else None)

    async def delete_opening(self, db: AsyncSession, opening_id: int, user_id: int) -> None:
        result = await db.execute(
            select(BidOpening).where(BidOpening.id == opening_id, BidOpening.is_deleted == 0)
        )
        opening = result.scalar_one_or_none()
        if opening is None:
            raise NotFoundException("开标记录不存在")
        opening.is_deleted = 1
        opening.updated_by = user_id
        await db.flush()

    async def get_by_tender(self, db: AsyncSession, tender_id: int) -> list:
        result = await db.execute(
            select(BidOpening).where(
                BidOpening.tender_id == tender_id,
                BidOpening.is_deleted == 0,
            ).order_by(BidOpening.id.desc())
        )
        openings = result.scalars().all()

        tender_result = await db.execute(
            select(Tender.title, Tender.tender_no).where(Tender.id == tender_id)
        )
        row = tender_result.first()
        tender_title = row[0] if row else None
        tender_no = row[1] if row else None

        return [self._to_dict(o, tender_title=tender_title, tender_no=tender_no) for o in openings]


opening_service = OpeningService()
