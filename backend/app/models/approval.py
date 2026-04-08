"""
审批模型
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base
from app.models.base import BaseModel

_pk_type = Integer if settings.DB_TYPE == "sqlite" else BigInteger


class ApprovalInstance(BaseModel):
    """审批实例"""
    __tablename__ = "approval_instance"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    biz_type: Mapped[str] = mapped_column(String(50), nullable=False)
    biz_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    initiator_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    approver_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    result_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ApprovalRecord(Base):
    """审批记录"""
    __tablename__ = "approval_record"

    id: Mapped[int] = mapped_column(_pk_type, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    operator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
