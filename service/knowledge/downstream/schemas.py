"""知识库管理模块 - downstream/schemas

请求/响应 Schema 定义
"""
from typing import Any, Literal

from pydantic import BaseModel, Field


class ImportInterfacesRequest(BaseModel):
    """importinterfaces请求"""
    module_id: int | None = Field(default=None, ge=1)
    catalog_id: int | None = Field(default=None, ge=1)
    items: list[dict[str, Any]] | None = None


class ImportInterfacesResult(BaseModel):
    """importinterfaces结果"""
    created: int
    updated: int
    skipped: int
    interface_ids: list[int]
