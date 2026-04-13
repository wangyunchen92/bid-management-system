"""
标书编制模型
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BidProject(BaseModel):
    """标书项目表"""
    __tablename__ = "bid_project"

    tender_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    doc_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", server_default="DRAFT")
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    leader_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class BidSection(BaseModel):
    """标书章节表"""
    __tablename__ = "bid_section"

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    section_type: Mapped[str] = mapped_column(String(20), nullable=False, default="AI_GENERATE", server_default="AI_GENERATE")
    # section_type: TEMPLATE(格式模板) / MANUAL(手动填写) / LIBRARY(资质引用) / AI_GENERATE(AI生成) / ATTACHMENT(附件)
    template_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # 关联知识库模板 ID（TEMPLATE 类型用）
    assignee_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
