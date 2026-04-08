"""
ORM 模型基类
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base

_pk_type = Integer if settings.DB_TYPE == "sqlite" else BigInteger


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(),
    )
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int] = mapped_column(BigInteger, nullable=True)
    is_deleted: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0",
    )


class BaseModel(Base, AuditMixin):
    __abstract__ = True

    id: Mapped[int] = mapped_column(_pk_type, primary_key=True, autoincrement=True)
