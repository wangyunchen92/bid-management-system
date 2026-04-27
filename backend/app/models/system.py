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
    dept_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="USER", server_default="USER")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class SysDepartment(BaseModel):
    """部门表"""
    __tablename__ = "sys_department"

    dept_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dept_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    leader_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")


class SysRole(BaseModel):
    """角色表"""
    __tablename__ = "sys_role"

    role_name: Mapped[str] = mapped_column(String(50), nullable=False)
    role_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")


class SysUserRole(Base):
    """用户角色关联表"""
    __tablename__ = "sys_user_role"

    id: Mapped[int] = mapped_column(_pk_type, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


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


class SysEnterpriseProfile(BaseModel):
    """企业信息配置（单行记录，id 永远为 1）—— 标书模板的占位符填值数据源"""
    __tablename__ = "sys_enterprise_profile"

    # 基础信息
    company_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    company_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    company_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_fax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_zipcode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    company_credit_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_bank: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_bank_account: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 详情
    company_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_founded: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_business_term: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 法定代表人
    legal_person_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    legal_person_gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    legal_person_age: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    legal_person_title: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # 授权代表
    authorized_rep_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    authorized_rep_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
