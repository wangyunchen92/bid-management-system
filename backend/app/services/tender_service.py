"""
招标管理服务
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException
from app.common.pagination import PaginationParams, paginate
from app.models.tender import Tender
from app.models.system import SysUser
from app.schemas.tender import TenderCreate, TenderUpdate, TenderResponse, TenderCalendarItem, TenderStats


class TenderService:

    async def _get_follower_name(self, db: AsyncSession, follower_id: Optional[int]) -> Optional[str]:
        if not follower_id:
            return None
        result = await db.execute(select(SysUser.real_name).where(SysUser.id == follower_id))
        return result.scalar_one_or_none()

    async def _tender_to_dict(self, db: AsyncSession, tender: Tender) -> dict:
        d = TenderResponse.model_validate(tender).model_dump()
        d["follower_name"] = await self._get_follower_name(db, tender.follower_id)
        # Decimal -> float for JSON
        if d.get("budget_amount") is not None:
            d["budget_amount"] = float(d["budget_amount"])
        if d.get("deposit_amount") is not None:
            d["deposit_amount"] = float(d["deposit_amount"])
        return d

    async def list_tenders(self, db: AsyncSession, params: PaginationParams,
                           keyword: Optional[str] = None, tender_method: Optional[str] = None,
                           info_source: Optional[str] = None, status: Optional[str] = None,
                           follower_id: Optional[int] = None,
                           start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        query = select(Tender).where(Tender.is_deleted == 0)

        if keyword:
            query = query.where(or_(Tender.title.contains(keyword), Tender.tender_no.contains(keyword)))
        if tender_method:
            query = query.where(Tender.tender_method == tender_method)
        if info_source:
            query = query.where(Tender.info_source == info_source)
        if status:
            query = query.where(Tender.status == status)
        if follower_id:
            query = query.where(Tender.follower_id == follower_id)
        if start_date:
            query = query.where(Tender.open_bid_time >= start_date)
        if end_date:
            query = query.where(Tender.open_bid_time <= end_date)

        result = await paginate(db, query, params, sort_column=Tender.id)
        items = []
        for t in result["items"]:
            items.append(await self._tender_to_dict(db, t))
        result["items"] = items
        return result

    async def create_tender(self, db: AsyncSession, data: TenderCreate, user_id: int) -> dict:
        tender = Tender(**data.model_dump(), created_by=user_id, updated_by=user_id)
        db.add(tender)
        await db.flush()
        await db.refresh(tender)
        return await self._tender_to_dict(db, tender)

    async def get_tender(self, db: AsyncSession, tender_id: int) -> dict:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")
        return await self._tender_to_dict(db, tender)

    async def update_tender(self, db: AsyncSession, tender_id: int, data: TenderUpdate, user_id: int) -> dict:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")

        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        for key, value in update_data.items():
            setattr(tender, key, value)
        await db.flush()
        await db.refresh(tender)
        return await self._tender_to_dict(db, tender)

    async def delete_tender(self, db: AsyncSession, tender_id: int, user_id: int) -> None:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")
        tender.is_deleted = 1
        tender.updated_by = user_id
        await db.flush()

    async def update_status(self, db: AsyncSession, tender_id: int, status: str, user_id: int) -> dict:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")
        tender.status = status
        tender.updated_by = user_id
        await db.flush()
        await db.refresh(tender)
        return await self._tender_to_dict(db, tender)

    async def update_follower(self, db: AsyncSession, tender_id: int, follower_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id, Tender.is_deleted == 0)
        )
        tender = result.scalar_one_or_none()
        if tender is None:
            raise NotFoundException("招标信息不存在")
        tender.follower_id = follower_id
        tender.updated_by = user_id
        await db.flush()
        await db.refresh(tender)
        return await self._tender_to_dict(db, tender)

    async def get_calendar(self, db: AsyncSession, year: int, month: int) -> List[dict]:
        from calendar import monthrange
        start = datetime(year, month, 1)
        _, last_day = monthrange(year, month)
        end = datetime(year, month, last_day, 23, 59, 59)

        result = await db.execute(
            select(Tender).where(
                Tender.is_deleted == 0,
                or_(
                    Tender.reg_deadline.between(start, end),
                    Tender.deposit_deadline.between(start, end),
                    Tender.open_bid_time.between(start, end),
                )
            )
        )
        tenders = result.scalars().all()

        items = []
        for t in tenders:
            if t.reg_deadline and start <= t.reg_deadline <= end:
                items.append(TenderCalendarItem(
                    id=t.id, title=t.title,
                    date=t.reg_deadline.strftime("%Y-%m-%d"),
                    type="reg_deadline", label="报名截止",
                ).model_dump())
            if t.deposit_deadline and start <= t.deposit_deadline <= end:
                items.append(TenderCalendarItem(
                    id=t.id, title=t.title,
                    date=t.deposit_deadline.strftime("%Y-%m-%d"),
                    type="deposit_deadline", label="保证金截止",
                ).model_dump())
            if t.open_bid_time and start <= t.open_bid_time <= end:
                items.append(TenderCalendarItem(
                    id=t.id, title=t.title,
                    date=t.open_bid_time.strftime("%Y-%m-%d"),
                    type="open_bid", label="开标",
                ).model_dump())
        return items

    async def get_stats(self, db: AsyncSession) -> dict:
        result = await db.execute(
            select(Tender.status, func.count(Tender.id))
            .where(Tender.is_deleted == 0)
            .group_by(Tender.status)
        )
        status_counts = {row[0]: row[1] for row in result.all()}

        total = sum(status_counts.values())
        return TenderStats(
            total=total,
            pending=status_counts.get("PENDING", 0),
            decided_bid=status_counts.get("DECIDED_BID", 0),
            decided_give_up=status_counts.get("DECIDED_GIVE_UP", 0),
            composing=status_counts.get("COMPOSING", 0),
            submitted=status_counts.get("SUBMITTED", 0),
            opened=status_counts.get("OPENED", 0),
        ).model_dump()

    async def get_expiring(self, db: AsyncSession) -> List[dict]:
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=7)

        result = await db.execute(
            select(Tender).where(
                Tender.is_deleted == 0,
                Tender.status.in_(["PENDING", "DECIDED_BID", "COMPOSING"]),
                or_(
                    Tender.reg_deadline.between(now, deadline),
                    Tender.deposit_deadline.between(now, deadline),
                    Tender.open_bid_time.between(now, deadline),
                )
            ).order_by(Tender.reg_deadline.asc())
        )
        items = []
        for t in result.scalars().all():
            items.append(await self._tender_to_dict(db, t))
        return items


tender_service = TenderService()
