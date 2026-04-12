"""
企业资料库模型
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.models.base import BaseModel

_pk_type = Integer if settings.DB_TYPE == "sqlite" else BigInteger


class Qualification(BaseModel):
    """资质证书"""
    __tablename__ = "lib_qualification"

    cert_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cert_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cert_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    issuing_authority: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class Achievement(BaseModel):
    """业绩案例"""
    __tablename__ = "lib_achievement"

    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contract_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    completion_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    project_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class PersonnelCert(BaseModel):
    """人员证书"""
    __tablename__ = "lib_personnel_cert"

    person_name: Mapped[str] = mapped_column(String(50), nullable=False)
    cert_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cert_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cert_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class Product(BaseModel):
    """产品/设备"""
    __tablename__ = "lib_product"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
