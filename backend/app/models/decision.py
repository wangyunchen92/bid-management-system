"""
投标决策模型
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BidDecision(BaseModel):
    """投标决策表"""
    __tablename__ = "bid_decision"

    tender_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    win_probability: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    competitors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_result: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    approval_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    initiator_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
