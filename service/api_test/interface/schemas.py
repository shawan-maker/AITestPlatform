from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from service.core.enums import ApiInterfaceSource
from service.core.pagination import Paginated


class InterfaceCreateRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    catalog_id: int = Field(..., ge=1)
    module_id: int | None = Field(default=None, ge=1)
    method: str = Field(..., min_length=1, max_length=10)
    path: str = Field(..., min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=255)
    parameters: dict[str, Any] | None = None
    request_body: dict[str, Any] | None = None
    responses: list[Any] | None = None


class InterfaceUpdateRequest(BaseModel):
    catalog_id: int | None = Field(default=None, ge=1)
    module_id: int | None = Field(default=None, ge=1)
    method: str | None = Field(default=None, min_length=1, max_length=10)
    path: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=255)
    parameters: dict[str, Any] | None = None
    request_body: dict[str, Any] | None = None
    responses: list[Any] | None = None


class InterfaceOut(BaseModel):
    id: int
    project_id: int
    catalog_id: int | None
    module_id: int | None
    method: str
    path: str
    summary: str | None
    parameters: dict[str, Any]
    request_body: dict[str, Any] | None
    responses: list[Any]
    source: ApiInterfaceSource
    source_document_id: int | None
    source_document_version_id: int | None
    version: int
    is_current: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class InterfaceListQuery(BaseModel):
    project_id: int = Field(..., ge=1)
    catalog_id: int | None = Field(default=None, ge=1)
    q: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class InterfaceReorderRequest(BaseModel):
    catalog_id: int = Field(..., ge=1)
    ordered_ids: list[int] = Field(..., min_length=1)
    target_catalog_id: int | None = Field(default=None, ge=1)


class ImportPreviewItem(BaseModel):
    method: str
    path: str
    summary: str | None
    conflict: bool = False
    existing_interface_id: int | None = None


class ImportPreviewResult(BaseModel):
    document_id: int
    version_id: int
    items: list[ImportPreviewItem]


class ImportConfirmItem(BaseModel):
    method: str
    path: str
    summary: str | None = None
    parameters: dict[str, Any] | None = None
    request_body: dict[str, Any] | None = None
    responses: list[Any] | None = None


class ImportConfirmRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    catalog_id: int = Field(..., ge=1)
    module_id: int | None = Field(default=None, ge=1)
    document_id: int = Field(..., ge=1)
    version_id: int = Field(..., ge=1)
    mode: Literal["skip", "upsert"] = "skip"
    items: list[ImportConfirmItem] = Field(default_factory=list)


class ImportConfirmResult(BaseModel):
    created: int
    updated: int
    skipped: int
    interface_ids: list[int]
    dependency_inference_errors: list[str] = Field(default_factory=list)


PaginatedInterfaces = Paginated[InterfaceOut]
