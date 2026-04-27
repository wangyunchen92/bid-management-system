"""
系统管理 Schema
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---- 字典类型 ----

class DictTypeCreate(BaseModel):
    dict_name: str = Field(..., max_length=100)
    dict_code: str = Field(..., max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    status: int = Field(default=1)


class DictTypeUpdate(BaseModel):
    dict_name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    status: Optional[int] = Field(default=None)


class DictTypeResponse(BaseModel):
    id: int
    dict_name: str
    dict_code: str
    description: Optional[str] = None
    status: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- 字典项 ----

class DictItemCreate(BaseModel):
    item_label: str = Field(..., max_length=100)
    item_value: str = Field(..., max_length=100)
    sort_order: int = Field(default=0)
    status: int = Field(default=1)
    description: Optional[str] = Field(default=None, max_length=255)


class DictItemUpdate(BaseModel):
    item_label: Optional[str] = Field(default=None, max_length=100)
    item_value: Optional[str] = Field(default=None, max_length=100)
    sort_order: Optional[int] = Field(default=None)
    status: Optional[int] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=255)


class DictItemResponse(BaseModel):
    id: int
    dict_type_id: int
    item_label: str
    item_value: str
    sort_order: int
    status: int
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ========== 部门 ==========

class DepartmentCreate(BaseModel):
    dept_name: str = Field(..., max_length=100)
    dept_code: str = Field(..., max_length=50)
    parent_id: Optional[int] = Field(default=None)
    leader_id: Optional[int] = Field(default=None)
    sort_order: int = Field(default=0)
    status: int = Field(default=1)


class DepartmentUpdate(BaseModel):
    dept_name: Optional[str] = Field(default=None, max_length=100)
    parent_id: Optional[int] = Field(default=None)
    leader_id: Optional[int] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)
    status: Optional[int] = Field(default=None)


class DepartmentResponse(BaseModel):
    id: int
    dept_name: str
    dept_code: str
    parent_id: Optional[int] = None
    leader_id: Optional[int] = None
    sort_order: int = 0
    status: int = 1
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DepartmentTree(BaseModel):
    id: int
    dept_name: str
    dept_code: str
    parent_id: Optional[int] = None
    leader_id: Optional[int] = None
    sort_order: int = 0
    status: int = 1
    children: List["DepartmentTree"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ========== 用户管理 ==========

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    real_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=100)
    dept_id: Optional[int] = Field(default=None)
    position: Optional[str] = Field(default=None, max_length=50)
    role: str = Field(default="USER")
    status: int = Field(default=1)
    role_ids: List[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    real_name: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=100)
    dept_id: Optional[int] = Field(default=None)
    position: Optional[str] = Field(default=None, max_length=50)
    role: Optional[str] = Field(default=None)
    status: Optional[int] = Field(default=None)


class UserResponse(BaseModel):
    id: int
    username: str
    real_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    dept_id: Optional[int] = None
    dept_name: Optional[str] = None
    position: Optional[str] = None
    role: str = "USER"
    status: int = 1
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    roles: List[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ========== 角色 ==========

class RoleCreate(BaseModel):
    role_name: str = Field(..., max_length=50)
    role_code: str = Field(..., max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = Field(default=0)
    status: int = Field(default=1)


class RoleUpdate(BaseModel):
    role_name: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: Optional[int] = Field(default=None)
    status: Optional[int] = Field(default=None)


class RoleResponse(BaseModel):
    id: int
    role_name: str
    role_code: str
    description: Optional[str] = None
    sort_order: int = 0
    status: int = 1
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AssignRolesRequest(BaseModel):
    role_ids: List[int] = Field(default_factory=list)


# ---- 企业信息配置 ----

class EnterpriseProfile(BaseModel):
    """企业信息（标书模板占位符的数据源）"""
    company_name: str = Field(default="", max_length=200)
    company_address: Optional[str] = Field(default=None, max_length=500)
    company_phone: Optional[str] = Field(default=None, max_length=50)
    company_fax: Optional[str] = Field(default=None, max_length=50)
    company_zipcode: Optional[str] = Field(default=None, max_length=20)
    company_credit_code: Optional[str] = Field(default=None, max_length=50)
    company_bank: Optional[str] = Field(default=None, max_length=100)
    company_bank_account: Optional[str] = Field(default=None, max_length=100)
    company_type: Optional[str] = Field(default=None, max_length=100)
    company_founded: Optional[str] = Field(default=None, max_length=50)
    company_business_term: Optional[str] = Field(default=None, max_length=100)
    legal_person_name: Optional[str] = Field(default=None, max_length=50)
    legal_person_gender: Optional[str] = Field(default=None, max_length=10)
    legal_person_age: Optional[str] = Field(default=None, max_length=10)
    legal_person_title: Optional[str] = Field(default=None, max_length=50)
    authorized_rep_name: Optional[str] = Field(default=None, max_length=50)
    authorized_rep_phone: Optional[str] = Field(default=None, max_length=50)
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EnterpriseProfileUpdate(BaseModel):
    """全量更新企业信息（PUT 用，所有字段都是 Optional 以兼容部分修改）"""
    company_name: Optional[str] = Field(default=None, max_length=200)
    company_address: Optional[str] = Field(default=None, max_length=500)
    company_phone: Optional[str] = Field(default=None, max_length=50)
    company_fax: Optional[str] = Field(default=None, max_length=50)
    company_zipcode: Optional[str] = Field(default=None, max_length=20)
    company_credit_code: Optional[str] = Field(default=None, max_length=50)
    company_bank: Optional[str] = Field(default=None, max_length=100)
    company_bank_account: Optional[str] = Field(default=None, max_length=100)
    company_type: Optional[str] = Field(default=None, max_length=100)
    company_founded: Optional[str] = Field(default=None, max_length=50)
    company_business_term: Optional[str] = Field(default=None, max_length=100)
    legal_person_name: Optional[str] = Field(default=None, max_length=50)
    legal_person_gender: Optional[str] = Field(default=None, max_length=10)
    legal_person_age: Optional[str] = Field(default=None, max_length=10)
    legal_person_title: Optional[str] = Field(default=None, max_length=50)
    authorized_rep_name: Optional[str] = Field(default=None, max_length=50)
    authorized_rep_phone: Optional[str] = Field(default=None, max_length=50)
