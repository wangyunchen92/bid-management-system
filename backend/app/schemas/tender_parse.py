"""
招标文件解析 Schema
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TenderDocumentResponse(BaseModel):
    id: int
    project_id: Optional[int] = None
    tender_id: Optional[int] = None
    original_name: str
    file_size: int
    file_type: str
    page_count: Optional[int] = None
    parse_status: str = "PENDING"
    parse_result: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
