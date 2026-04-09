"""
标书知识库 Pydantic Schema
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KnowledgeTemplateCreate(BaseModel):
    title: str = Field(..., max_length=200)
    category: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = None
    source_project_id: Optional[int] = None
    tags: Optional[str] = Field(default=None, max_length=500)
    remark: Optional[str] = None


class KnowledgeTemplateUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = None
    source_project_id: Optional[int] = None
    tags: Optional[str] = Field(default=None, max_length=500)
    remark: Optional[str] = None


class KnowledgeTemplateResponse(BaseModel):
    id: int
    title: str
    category: Optional[str] = None
    content: Optional[str] = None
    source_project_id: Optional[int] = None
    tags: Optional[str] = None
    usage_count: int = 0
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    is_deleted: int = 0

    model_config = {"from_attributes": True}
