"""
统一响应格式
"""

import time
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    code: int = Field(default=200)
    message: str = Field(default="success")
    data: Optional[Any] = Field(default=None)
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class PageData(BaseModel):
    items: list = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    total_pages: int = Field(default=0)


def success(data: Any = None, message: str = "success") -> dict:
    return ResponseModel(code=200, message=message, data=data).model_dump()


def fail(message: str = "操作失败", code: int = 400, data: Any = None) -> dict:
    return ResponseModel(code=code, message=message, data=data).model_dump()


def page_response(items: list, total: int, page: int, page_size: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    page_data = PageData(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)
    return success(data=page_data.model_dump())
