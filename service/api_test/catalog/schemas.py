"""接口测试模块 - catalog/schemas

请求/响应 Schema 定义
"""
from datetime import datetime

from pydantic import BaseModel, Field


class CatalogCreateRequest(BaseModel):
    """目录创建请求"""
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int | None = Field(default=None, ge=1)


class CatalogUpdateRequest(BaseModel):
    """目录更新请求"""
    name: str | None = Field(default=None, min_length=1, max_length=100)


class CatalogMoveRequest(BaseModel):
    """目录移动请求"""
    parent_id: int | None = Field(default=None, ge=0, description="0 表示移到根级")
    sort_order: int | None = Field(default=None, ge=0)


class CatalogOut(BaseModel):
    """目录out"""
    id: int
    project_id: int
    parent_id: int | None
    name: str
    level: int
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CatalogTreeNode(CatalogOut):
    """目录treenode"""
    interface_count: int = 0
    children: list["CatalogTreeNode"] = Field(default_factory=list)
