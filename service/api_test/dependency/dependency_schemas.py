from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from service.core.enums import DependencyInferenceSource


class DependencyEdgeIn(BaseModel):
    to_api_id: int = Field(..., ge=1)
    seq: int = Field(..., ge=1)
    param_map: dict[str, Any] | None = None
    required: bool = True


class DependencyEdgeOut(BaseModel):
    id: int
    from_api_id: int
    to_api_id: int
    seq: int
    param_map: dict[str, Any] | None
    required: bool
    inference_source: DependencyInferenceSource
    confidence: float | None
    to_api_method: str
    to_api_path: str
    to_api_summary: str | None


class DependencyListOut(BaseModel):
    target_api_id: int
    dependency_group_id: int | None
    edges: list[DependencyEdgeOut]


class DependencyReplaceRequest(BaseModel):
    edges: list[DependencyEdgeIn] = Field(default_factory=list)


class DocPreviewOut(BaseModel):
    interface_id: int
    source: str
    source_document_id: int | None
    source_document_version_id: int | None
    doc: dict[str, Any]
    updated_at: datetime
