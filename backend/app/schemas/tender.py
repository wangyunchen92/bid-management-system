"""
招标 Schema
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TenderCreate(BaseModel):
    title: str = Field(..., max_length=200)
    tender_no: Optional[str] = Field(default=None, max_length=100)
    tender_unit: Optional[str] = Field(default=None, max_length=200)
    tender_method: Optional[str] = Field(default=None, max_length=50)
    info_source: Optional[str] = Field(default=None, max_length=50)
    province: Optional[str] = Field(default=None, max_length=50)
    city: Optional[str] = Field(default=None, max_length=50)
    budget_amount: Optional[Decimal] = Field(default=None)
    deposit_amount: Optional[Decimal] = Field(default=None)
    deposit_deadline: Optional[datetime] = Field(default=None)
    reg_deadline: Optional[datetime] = Field(default=None)
    open_bid_time: Optional[datetime] = Field(default=None)
    status: str = Field(default="PENDING")
    follower_id: Optional[int] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class TenderUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    tender_no: Optional[str] = Field(default=None, max_length=100)
    tender_unit: Optional[str] = Field(default=None, max_length=200)
    tender_method: Optional[str] = Field(default=None, max_length=50)
    info_source: Optional[str] = Field(default=None, max_length=50)
    province: Optional[str] = Field(default=None, max_length=50)
    city: Optional[str] = Field(default=None, max_length=50)
    budget_amount: Optional[Decimal] = Field(default=None)
    deposit_amount: Optional[Decimal] = Field(default=None)
    deposit_deadline: Optional[datetime] = Field(default=None)
    reg_deadline: Optional[datetime] = Field(default=None)
    open_bid_time: Optional[datetime] = Field(default=None)
    status: Optional[str] = Field(default=None)
    follower_id: Optional[int] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class TenderResponse(BaseModel):
    id: int
    title: str
    tender_no: Optional[str] = None
    tender_unit: Optional[str] = None
    tender_method: Optional[str] = None
    info_source: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    budget_amount: Optional[float] = None
    deposit_amount: Optional[float] = None
    deposit_deadline: Optional[datetime] = None
    reg_deadline: Optional[datetime] = None
    open_bid_time: Optional[datetime] = None
    status: str = "PENDING"
    follower_id: Optional[int] = None
    follower_name: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., max_length=20)


class UpdateFollowerRequest(BaseModel):
    follower_id: int = Field(...)


class TenderCalendarItem(BaseModel):
    id: int
    title: str
    date: str
    type: str
    label: str


class TenderStats(BaseModel):
    total: int = 0
    pending: int = 0
    decided_bid: int = 0
    decided_give_up: int = 0
    composing: int = 0
    submitted: int = 0
    opened: int = 0
