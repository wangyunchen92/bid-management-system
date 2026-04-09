"""
开标跟踪 Schema
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OpeningCreate(BaseModel):
    tender_id: int = Field(..., description="关联招标ID")
    opening_time: Optional[datetime] = Field(default=None)
    result: Optional[str] = Field(default=None, max_length=20, description="WIN/LOSE/INVALID/ABORTED")
    our_price: Optional[float] = Field(default=None)
    win_price: Optional[float] = Field(default=None)
    win_company: Optional[str] = Field(default=None, max_length=200)
    total_bidders: Optional[int] = Field(default=None)
    ranking: Optional[int] = Field(default=None)
    review_summary: Optional[str] = Field(default=None)
    lessons_learned: Optional[str] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class OpeningUpdate(BaseModel):
    opening_time: Optional[datetime] = Field(default=None)
    result: Optional[str] = Field(default=None, max_length=20)
    our_price: Optional[float] = Field(default=None)
    win_price: Optional[float] = Field(default=None)
    win_company: Optional[str] = Field(default=None, max_length=200)
    total_bidders: Optional[int] = Field(default=None)
    ranking: Optional[int] = Field(default=None)
    review_summary: Optional[str] = Field(default=None)
    lessons_learned: Optional[str] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class OpeningResponse(BaseModel):
    id: int
    tender_id: int
    tender_title: Optional[str] = None
    tender_no: Optional[str] = None
    opening_time: Optional[datetime] = None
    result: Optional[str] = None
    our_price: Optional[float] = None
    win_price: Optional[float] = None
    win_company: Optional[str] = None
    total_bidders: Optional[int] = None
    ranking: Optional[int] = None
    review_summary: Optional[str] = None
    lessons_learned: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
