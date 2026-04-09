"""
标书知识库模型
"""

from typing import Optional

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class KnowledgeTemplate(BaseModel):
    """知识库模板表"""
    __tablename__ = "knowledge_template"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
