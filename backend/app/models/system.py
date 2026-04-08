"""
系统模型 - 用户表
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import SmallInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


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
