from datetime import datetime

from pydantic import BaseModel, Field


class CatalogCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int | None = Field(default=None, ge=1)


class CatalogUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class CatalogMoveRequest(BaseModel):
    parent_id: int | None = Field(default=None, ge=1)
    sort_order: int | None = Field(default=None, ge=0)


class CatalogOut(BaseModel):
    id: int
    project_id: int
    parent_id: int | None
    name: str
    level: int
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CatalogTreeNode(CatalogOut):
    interface_count: int = 0
    children: list["CatalogTreeNode"] = Field(default_factory=list)
