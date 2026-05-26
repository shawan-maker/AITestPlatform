"""需求与候选 Pydantic 模型（请求/响应）。"""

from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import (
    IndexStatus,
    RequirementSourceType,
    RequirementStatus,
)
from service.core.pagination import Paginated


class RequirementListQuery(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    title: str | None = None
    project_name: str | None = None
    source_type: RequirementSourceType | None = None
    module_id: int | None = Field(default=None, ge=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class RequirementCreateRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    module_id: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=255)
    doc_no: str | None = Field(default=None, max_length=100)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=4)
    status: RequirementStatus = RequirementStatus.draft


class RequirementUpdateRequest(BaseModel):
    module_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    doc_no: str | None = Field(default=None, max_length=100)
    description: str | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    status: RequirementStatus | None = None


class RequirementBrief(BaseModel):
    id: int
    project_id: int
    project_name: str
    module_id: int | None
    module_name: str | None
    title: str
    source_type: RequirementSourceType
    priority: int
    status: RequirementStatus
    created_by_username: str | None
    created_at: datetime
    updated_at: datetime


class RequirementDetail(RequirementBrief):
    doc_no: str | None
    description: str | None
    source_document_id: int | None
    source_document_version_id: int | None
    source_version_label: str | None
    index_status: IndexStatus
    indexed_at: datetime | None
    linked_case_count: int = 0


class RequirementDeleteResult(BaseModel):
    linked_case_count: int


PaginatedRequirements = Paginated[RequirementBrief]


class CandidateListQuery(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    title: str | None = None
    module_id: int | None = Field(default=None, ge=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CandidateBrief(BaseModel):
    id: int
    project_id: int
    project_name: str
    module_id: int | None
    module_name: str | None
    title: str
    source_document_id: int
    source_document_version_id: int
    source_version_label: str
    index_status: IndexStatus
    indexed_at: datetime | None
    created_at: datetime


class CandidateDetail(CandidateBrief):
    description: str | None
    created_by_username: str | None


class CandidateConfirmRequest(BaseModel):
    module_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=4)
    status: RequirementStatus = RequirementStatus.draft


PaginatedCandidates = Paginated[CandidateBrief]
