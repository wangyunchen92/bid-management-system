"""
标书编制 Schema
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ========== 标书项目 ==========

class BidProjectCreate(BaseModel):
    tender_id: Optional[int] = Field(default=None)
    title: str = Field(..., max_length=200)
    doc_type: Optional[str] = Field(default=None, max_length=50)
    status: str = Field(default="DRAFT")
    deadline: Optional[datetime] = Field(default=None)
    leader_id: Optional[int] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class BidProjectUpdate(BaseModel):
    tender_id: Optional[int] = Field(default=None)
    title: Optional[str] = Field(default=None, max_length=200)
    doc_type: Optional[str] = Field(default=None, max_length=50)
    status: Optional[str] = Field(default=None)
    deadline: Optional[datetime] = Field(default=None)
    leader_id: Optional[int] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class BidProjectResponse(BaseModel):
    id: int
    tender_id: Optional[int] = None
    tender_title: Optional[str] = None
    title: str
    doc_type: Optional[str] = None
    status: str = "DRAFT"
    deadline: Optional[datetime] = None
    leader_id: Optional[int] = None
    leader_name: Optional[str] = None
    remark: Optional[str] = None
    section_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    model_config = {"from_attributes": True}


# ========== 标书章节 ==========

class BidSectionCreate(BaseModel):
    project_id: int = Field(...)
    parent_id: Optional[int] = Field(default=None)
    title: str = Field(..., max_length=200)
    content: Optional[str] = Field(default=None)
    sort_order: int = Field(default=0)
    assignee_id: Optional[int] = Field(default=None)
    status: str = Field(default="PENDING")


class BidSectionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)
    assignee_id: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    parent_id: Optional[int] = Field(default=None)


class BidSectionResponse(BaseModel):
    id: int
    project_id: int
    parent_id: Optional[int] = None
    title: str
    content: Optional[str] = None
    sort_order: int = 0
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    status: str = "PENDING"
    word_count: int = 0
    children: List["BidSectionResponse"] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


BidSectionResponse.model_rebuild()


class ReorderSectionsRequest(BaseModel):
    section_ids: List[int] = Field(...)
