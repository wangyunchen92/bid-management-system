"""
系统管理 Schema
"""

from datetime import datetime
from typing import Optional

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
