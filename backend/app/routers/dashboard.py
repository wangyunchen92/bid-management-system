"""
仪表盘统计路由 /api/v1/dashboard/*
直接在 router 中查询（仪表盘是只读聚合，不需要 service 层）
"""

from datetime import datetime, timedelta, timezone, date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, get_current_user_id
from app.common.response import success
from app.models.tender import Tender
from app.models.opening import BidOpening
from app.models.approval import ApprovalInstance
from app.models.system import SysUser

router = APIRouter()

STATUS_LABELS = {
    "PENDING": "待评估",
    "DECIDED_BID": "已决策-投标",
    "DECIDED_GIVE_UP": "已决策-放弃",
    "COMPOSING": "编制中",
    "SUBMITTED": "已提交",
    "OPENED": "已开标",
}

ACTIVE_STATUSES = ["PENDING", "DECIDED_BID", "COMPOSING", "SUBMITTED"]


@router.get("/stats", summary="仪表盘统计数据")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    week_later = now + timedelta(days=7)

    # ── 1. cards ──────────────────────────────────────────────
    # active_tenders
    active_result = await db.execute(
        select(func.count(Tender.id)).where(
            Tender.is_deleted == 0,
            Tender.status.in_(ACTIVE_STATUSES),
        )
    )
    active_tenders = active_result.scalar() or 0

    # win_count_year + total opening count for win_rate
    opening_result = await db.execute(
        select(BidOpening.result, func.count(BidOpening.id))
        .where(BidOpening.is_deleted == 0)
        .group_by(BidOpening.result)
    )
    opening_counts = {row[0]: row[1] for row in opening_result.all()}
    total_openings = sum(opening_counts.values())

    win_year_result = await db.execute(
        select(func.count(BidOpening.id)).where(
            BidOpening.is_deleted == 0,
            BidOpening.result == "WIN",
            BidOpening.created_at >= year_start,
        )
    )
    win_count_year = win_year_result.scalar() or 0

    total_wins = opening_counts.get("WIN", 0)
    win_rate = round(total_wins / total_openings * 100, 1) if total_openings > 0 else 0.0

    # expiring_7days
    expiring_count_result = await db.execute(
        select(func.count(Tender.id)).where(
            Tender.is_deleted == 0,
            or_(
                Tender.reg_deadline.between(now, week_later),
                Tender.deposit_deadline.between(now, week_later),
                Tender.open_bid_time.between(now, week_later),
            ),
        )
    )
    expiring_7days = expiring_count_result.scalar() or 0

    cards = {
        "active_tenders": active_tenders,
        "win_count_year": win_count_year,
        "win_rate": win_rate,
        "expiring_7days": expiring_7days,
    }

    # ── 2. status_distribution ────────────────────────────────
    status_dist_result = await db.execute(
        select(Tender.status, func.count(Tender.id))
        .where(Tender.is_deleted == 0)
        .group_by(Tender.status)
    )
    status_map = {row[0]: row[1] for row in status_dist_result.all()}
    status_distribution = [
        {"status": s, "label": STATUS_LABELS.get(s, s), "count": status_map.get(s, 0)}
        for s in STATUS_LABELS
    ]

    # ── 3. monthly_trend（近6个月）────────────────────────────
    months = []
    for i in range(5, -1, -1):
        # 计算各月第一天
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    monthly_trend = []
    for y, m in months:
        month_start = datetime(y, m, 1, tzinfo=timezone.utc)
        if m == 12:
            month_end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(y, m + 1, 1, tzinfo=timezone.utc)

        # bid_count: 该月创建的且状态为DECIDED_BID/COMPOSING/SUBMITTED/OPENED（决策通过）
        bid_cnt_result = await db.execute(
            select(func.count(Tender.id)).where(
                Tender.is_deleted == 0,
                Tender.status.in_(["DECIDED_BID", "COMPOSING", "SUBMITTED", "OPENED"]),
                Tender.created_at >= month_start,
                Tender.created_at < month_end,
            )
        )
        bid_count = bid_cnt_result.scalar() or 0

        # win_count: 该月创建的开标记录中 result=WIN
        win_cnt_result = await db.execute(
            select(func.count(BidOpening.id)).where(
                BidOpening.is_deleted == 0,
                BidOpening.result == "WIN",
                BidOpening.created_at >= month_start,
                BidOpening.created_at < month_end,
            )
        )
        win_count = win_cnt_result.scalar() or 0

        monthly_trend.append({
            "month": f"{y}-{m:02d}",
            "bid_count": bid_count,
            "win_count": win_count,
        })

    # ── 4. expiring_list（7天内截止，最多10条）────────────────
    expiring_result = await db.execute(
        select(Tender).where(
            Tender.is_deleted == 0,
            or_(
                Tender.reg_deadline.between(now, week_later),
                Tender.deposit_deadline.between(now, week_later),
                Tender.open_bid_time.between(now, week_later),
            ),
        ).order_by(Tender.reg_deadline.asc()).limit(10)
    )
    tenders_expiring = expiring_result.scalars().all()

    expiring_list = []
    for t in tenders_expiring:
        # 选取最近的截止日期
        candidates = []
        if t.reg_deadline:
            candidates.append(("reg_deadline", t.reg_deadline))
        if t.deposit_deadline:
            candidates.append(("deposit_deadline", t.deposit_deadline))
        if t.open_bid_time:
            candidates.append(("open_bid_time", t.open_bid_time))

        for dtype, dtime in candidates:
            if now <= dtime.replace(tzinfo=timezone.utc) if dtime.tzinfo is None else dtime <= week_later:
                dtime_aware = dtime.replace(tzinfo=timezone.utc) if dtime.tzinfo is None else dtime
                days_left = (dtime_aware.date() - now.date()).days
                expiring_list.append({
                    "id": t.id,
                    "title": t.title,
                    "deadline_type": dtype,
                    "deadline": dtime.strftime("%Y-%m-%d"),
                    "days_left": days_left,
                })
                break  # 每个 tender 只取最早的一个

    # ── 5. pending_approvals（当前用户待审批，最多5条）─────────
    approvals_result = await db.execute(
        select(ApprovalInstance, SysUser.real_name)
        .join(SysUser, SysUser.id == ApprovalInstance.initiator_id, isouter=True)
        .where(
            ApprovalInstance.is_deleted == 0,
            ApprovalInstance.approver_id == user_id,
            ApprovalInstance.status == "PENDING",
        )
        .order_by(ApprovalInstance.created_at.desc())
        .limit(5)
    )
    pending_approvals = []
    for inst, initiator_name in approvals_result.all():
        pending_approvals.append({
            "id": inst.id,
            "title": inst.title,
            "initiator_name": initiator_name or "",
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
        })

    return success(data={
        "cards": cards,
        "status_distribution": status_distribution,
        "monthly_trend": monthly_trend,
        "expiring_list": expiring_list,
        "pending_approvals": pending_approvals,
    })
