"""
系统模型 - 用户表
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Integer, SmallInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.database import Base
from app.models.base import BaseModel

_pk_type = Integer if settings.DB_TYPE == "sqlite" else BigInteger


class SysUser(BaseModel):
    __tablename__ = "sys_user"

    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="USER", server_default="USER")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SysDictType(BaseModel):
    __tablename__ = "sys_dict_type"

    dict_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dict_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")


class SysDictItem(Base):
    __tablename__ = "sys_dict_item"

    id: Mapped[int] = mapped_column(_pk_type, primary_key=True, autoincrement=True)
    dict_type_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    item_label: Mapped[str] = mapped_column(String(100), nullable=False)
    item_value: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
