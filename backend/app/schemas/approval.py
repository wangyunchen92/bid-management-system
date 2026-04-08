"""
审批 Schema
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SubmitApprovalRequest(BaseModel):
    title: str = Field(..., max_length=200)
    biz_type: str = Field(..., max_length=50)
    biz_id: Optional[int] = Field(default=None)
    approver_id: int = Field(...)


class ApproveRequest(BaseModel):
    comment: Optional[str] = Field(default=None)


class RejectRequest(BaseModel):
    comment: Optional[str] = Field(default=None)


class TransferRequest(BaseModel):
    to_user_id: int = Field(...)
    comment: Optional[str] = Field(default=None)


class ApprovalInstanceResponse(BaseModel):
    id: int
    title: str
    biz_type: str
    biz_id: Optional[int] = None
    initiator_id: int
    initiator_name: Optional[str] = None
    approver_id: int
    approver_name: Optional[str] = None
    status: str = "PENDING"
    result_comment: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApprovalRecordResponse(BaseModel):
    id: int
    instance_id: int
    operator_id: int
    operator_name: Optional[str] = None
    action: str
    comment: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApprovalDetailResponse(BaseModel):
    instance: ApprovalInstanceResponse
    records: List[ApprovalRecordResponse] = []
