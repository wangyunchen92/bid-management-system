"""标书检测报告模型"""

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BidCheckReport(BaseModel):
    """标书检测报告表"""
    __tablename__ = "bid_check_report"

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PASS")
    rule_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    ai_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_items: Mapped[str] = mapped_column(Text, nullable=True)  # JSON
    ai_items: Mapped[str] = mapped_column(Text, nullable=True)    # JSON
    summary: Mapped[str] = mapped_column(Text, nullable=True)
