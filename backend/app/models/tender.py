"""
招标信息模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Tender(BaseModel):
    """招标信息表"""
    __tablename__ = "tender"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    tender_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tender_unit: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tender_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    info_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    budget_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    deposit_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    deposit_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reg_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    open_bid_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    follower_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
