"""标书检测 Schema"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DetectItem(BaseModel):
    """单条检查项"""
    category: str = Field(..., description="检查类别")
    check_name: str = Field(..., description="检查项名称")
    status: str = Field(..., description="PASS / WARNING / FAIL")
    source: Optional[str] = Field(default=None, description="招标文件依据引用")
    detail: str = Field(..., description="检查结果说明")
    suggestion: Optional[str] = Field(default=None, description="改进建议")
    section_title: Optional[str] = Field(default=None, description="关联的标书章节")


class DetectReportResponse(BaseModel):
    """检测报告完整响应"""
    id: int
    project_id: int
    total_score: int = 0
    status: str = "PASS"
    rule_score: int = 100
    ai_score: int = 0
    rule_items: List[DetectItem] = []
    ai_items: List[DetectItem] = []
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None


class DetectReportListItem(BaseModel):
    """检测报告列表项"""
    id: int
    total_score: int = 0
    status: str = "PASS"
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
