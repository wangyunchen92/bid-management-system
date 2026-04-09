"""
招标文件模型
"""

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TenderDocument(BaseModel):
    __tablename__ = "tender_document"

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    tender_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    parse_result: Mapped[str] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
