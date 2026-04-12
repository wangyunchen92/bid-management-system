"""
企业资料库 Schema
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ================================================================== #
#  资质证书
# ================================================================== #

class QualificationCreate(BaseModel):
    cert_name: str = Field(..., max_length=200)
    cert_type: Optional[str] = Field(default=None, max_length=50)
    cert_no: Optional[str] = Field(default=None, max_length=100)
    issuing_authority: Optional[str] = Field(default=None, max_length=200)
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: int = Field(default=1)
    remark: Optional[str] = None
    file_path: Optional[str] = Field(default=None)


class QualificationUpdate(BaseModel):
    cert_name: Optional[str] = Field(default=None, max_length=200)
    cert_type: Optional[str] = Field(default=None, max_length=50)
    cert_no: Optional[str] = Field(default=None, max_length=100)
    issuing_authority: Optional[str] = Field(default=None, max_length=200)
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: Optional[int] = None
    remark: Optional[str] = None


class QualificationResponse(BaseModel):
    id: int
    cert_name: str
    cert_type: Optional[str] = None
    cert_no: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: int
    remark: Optional[str] = None
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ================================================================== #
#  业绩案例
# ================================================================== #

class AchievementCreate(BaseModel):
    project_name: str = Field(..., max_length=200)
    client_name: Optional[str] = Field(default=None, max_length=200)
    contract_amount: Optional[float] = None
    completion_date: Optional[datetime] = None
    project_type: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    remark: Optional[str] = None
    file_path: Optional[str] = Field(default=None)


class AchievementUpdate(BaseModel):
    project_name: Optional[str] = Field(default=None, max_length=200)
    client_name: Optional[str] = Field(default=None, max_length=200)
    contract_amount: Optional[float] = None
    completion_date: Optional[datetime] = None
    project_type: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    remark: Optional[str] = None


class AchievementResponse(BaseModel):
    id: int
    project_name: str
    client_name: Optional[str] = None
    contract_amount: Optional[float] = None
    completion_date: Optional[datetime] = None
    project_type: Optional[str] = None
    description: Optional[str] = None
    remark: Optional[str] = None
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ================================================================== #
#  人员证书
# ================================================================== #

class PersonnelCertCreate(BaseModel):
    person_name: str = Field(..., max_length=50)
    cert_name: str = Field(..., max_length=200)
    cert_no: Optional[str] = Field(default=None, max_length=100)
    cert_type: Optional[str] = Field(default=None, max_length=50)
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: int = Field(default=1)
    remark: Optional[str] = None
    file_path: Optional[str] = Field(default=None)


class PersonnelCertUpdate(BaseModel):
    person_name: Optional[str] = Field(default=None, max_length=50)
    cert_name: Optional[str] = Field(default=None, max_length=200)
    cert_no: Optional[str] = Field(default=None, max_length=100)
    cert_type: Optional[str] = Field(default=None, max_length=50)
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: Optional[int] = None
    remark: Optional[str] = None


class PersonnelCertResponse(BaseModel):
    id: int
    person_name: str
    cert_name: str
    cert_no: Optional[str] = None
    cert_type: Optional[str] = None
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: int
    remark: Optional[str] = None
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ================================================================== #
#  产品/设备
# ================================================================== #

class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    model: Optional[str] = Field(default=None, max_length=100)
    brand: Optional[str] = Field(default=None, max_length=100)
    quantity: int = Field(default=1)
    unit: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    remark: Optional[str] = None
    file_path: Optional[str] = Field(default=None)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    model: Optional[str] = Field(default=None, max_length=100)
    brand: Optional[str] = Field(default=None, max_length=100)
    quantity: Optional[int] = None
    unit: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = None
    remark: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    model: Optional[str] = None
    brand: Optional[str] = None
    quantity: int
    unit: Optional[str] = None
    description: Optional[str] = None
    remark: Optional[str] = None
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
