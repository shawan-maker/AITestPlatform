from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import (
    DefectCategory,
    DefectHistoryAction,
    DefectPriority,
    DefectSeverity,
    DefectSourceType,
    DefectStatus,
)
from service.core.pagination import Paginated


class DefectListQuery(BaseModel):
    project_id: int = Field(ge=1)
    q: str | None = None
    id: int | None = Field(default=None, ge=1)
    severity: DefectSeverity | None = None
    priority: DefectPriority | None = None
    status: DefectStatus | None = None
    defect_category: DefectCategory | None = None
    created_by_id: int | None = Field(default=None, ge=1)
    assignee_id: int | None = Field(default=None, ge=1)
    created_from: datetime | None = None
    created_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class DefectManualCreateRequest(BaseModel):
    project_id: int = Field(ge=1)
    module_id: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=1, max_length=255)
    defect_category: DefectCategory = DefectCategory.other
    steps: str | None = None
    severity: DefectSeverity = DefectSeverity.normal
    priority: DefectPriority = DefectPriority.medium
    root_cause: str | None = None
    assignee_id: int | None = Field(default=None, ge=1)
    comment: str | None = None


class DefectUpdateRequest(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    module_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    defect_category: DefectCategory | None = None
    steps: str | None = None
    severity: DefectSeverity | None = None
    priority: DefectPriority | None = None
    root_cause: str | None = None


class DefectTransitionRequest(BaseModel):
    status: DefectStatus
    assignee_id: int | None = Field(default=None, ge=1)
    comment: str | None = Field(default=None, min_length=1)


class DefectCommentCreateRequest(BaseModel):
    content: str = Field(min_length=1)


class DefectListItemOut(BaseModel):
    id: int
    defect_code: str | None = None
    title: str
    severity: DefectSeverity
    priority: DefectPriority
    status: DefectStatus
    defect_category: DefectCategory
    assignee_id: int | None = None
    assignee_name: str | None = None
    created_by_id: int | None = None
    created_by_name: str | None = None
    created_at: datetime


class DefectSourceOut(BaseModel):
    source_type: DefectSourceType
    source_run_id: int | None = None
    source_case_id: int | None = None
    case_name: str | None = None
    run_label: str | None = None
    source_unreachable: bool = False


class DefectCommentOut(BaseModel):
    id: int
    content: str
    created_by_id: int | None = None
    created_by_name: str | None = None
    created_at: datetime


class DefectHistoryOut(BaseModel):
    id: int
    action: DefectHistoryAction
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    created_at: datetime


class DefectStatusTimelineItem(BaseModel):
    status: DefectStatus
    at: datetime
    operator_id: int | None = None
    operator_name: str | None = None


class DefectDetailOut(BaseModel):
    id: int
    defect_code: str | None = None
    project_id: int
    project_name: str | None = None
    module_id: int | None = None
    module_name: str | None = None
    title: str
    defect_category: DefectCategory
    steps: str | None = None
    root_cause: str | None = None
    severity: DefectSeverity
    priority: DefectPriority
    status: DefectStatus
    external_key: str | None = None
    assignee_id: int | None = None
    assignee_name: str | None = None
    created_by_id: int | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    source: DefectSourceOut
    comments: list[DefectCommentOut] = []
    history: list[DefectHistoryOut] = []
    status_timeline: list[DefectStatusTimelineItem] = []


PaginatedDefects = Paginated[DefectListItemOut]


class DefectBatchDeleteRequest(BaseModel):
    defect_ids: list[int] = Field(..., min_length=1, max_length=50)


class DefectBatchDeleteFailure(BaseModel):
    defect_id: int
    message: str


class DefectBatchDeleteResult(BaseModel):
    deleted_ids: list[int]
    failures: list[DefectBatchDeleteFailure]
