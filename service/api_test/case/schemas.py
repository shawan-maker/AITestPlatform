from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from service.core.enums import ApiCaseKind, ExecStatus, ReviewStatus
from service.core.pagination import Paginated


class GeneratePreviewRequest(BaseModel):
    environment_id: int | None = Field(default=None, ge=1)
    user_prompt: str | None = None


class BaseCasePreviewItem(BaseModel):
    index: int
    name: str
    steps: list[str]
    dependencies: list[str]
    expected: list[str]


class GeneratePreviewResult(BaseModel):
    session_id: int
    base_cases: list[BaseCasePreviewItem]


class GenerateConfirmRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    selected_indexes: list[int] = Field(..., min_length=1)
    environment_id: int = Field(..., ge=1)


class GenerateConfirmResult(BaseModel):
    created_base_case_ids: list[int]
    created_case_ids: list[int]
    run_errors: list[str] = Field(default_factory=list)


class CaseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    case_payload: dict[str, Any] | None = None


class CaseOut(BaseModel):
    id: int
    project_id: int
    interface_id: int | None
    title: str
    case_kind: ApiCaseKind
    sort_order: int
    case_payload: dict[str, Any]
    review_status: ReviewStatus
    exec_status: ExecStatus
    generation_count: int
    default_file_id: int | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CaseBatchDeleteRequest(BaseModel):
    case_ids: list[int] = Field(..., min_length=1)


class CaseDebugRunRequest(BaseModel):
    environment_id: int = Field(..., ge=1)


class RunRecordOut(BaseModel):
    id: int
    case_name: str
    status: str
    run_type: str
    duration_ms: int | None
    error_message: str | None
    created_at: datetime


PaginatedCases = Paginated[CaseOut]
PaginatedRunRecords = Paginated[RunRecordOut]
