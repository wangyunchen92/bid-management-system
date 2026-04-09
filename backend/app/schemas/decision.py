"""
投标决策 Schema
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class DecisionCreate(BaseModel):
    tender_id: int = Field(..., description="关联招标ID")
    decision_reason: Optional[str] = Field(default=None)
    risk_analysis: Optional[str] = Field(default=None)
    estimated_amount: Optional[Decimal] = Field(default=None)
    win_probability: Optional[int] = Field(default=None, ge=0, le=100)
    competitors: Optional[str] = Field(default=None)
    approver_id: int = Field(..., description="审批人ID")
    remark: Optional[str] = Field(default=None)


class DecisionUpdate(BaseModel):
    decision_reason: Optional[str] = Field(default=None)
    risk_analysis: Optional[str] = Field(default=None)
    estimated_amount: Optional[Decimal] = Field(default=None)
    win_probability: Optional[int] = Field(default=None, ge=0, le=100)
    competitors: Optional[str] = Field(default=None)
    remark: Optional[str] = Field(default=None)


class DecisionResponse(BaseModel):
    id: int
    tender_id: int
    tender_title: Optional[str] = None
    tender_no: Optional[str] = None
    decision_reason: Optional[str] = None
    risk_analysis: Optional[str] = None
    estimated_amount: Optional[float] = None
    win_probability: Optional[int] = None
    competitors: Optional[str] = None
    decision_result: str = "PENDING"
    approval_id: Optional[int] = None
    approval_status: Optional[str] = None
    initiator_id: int
    initiator_name: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
