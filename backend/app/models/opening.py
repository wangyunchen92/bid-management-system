"""
开标跟踪模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BidOpening(BaseModel):
    """开标跟踪表"""
    __tablename__ = "bid_opening"

    tender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    opening_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    our_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    win_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    win_company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    total_bidders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ranking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    review_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
