from pydantic import BaseModel, Field

from service.core.enums import (
    DefectCategory,
    DefectPriority,
    DefectSeverity,
    DefectSourceType,
    DefectStatus,
)


class DefectCreateRequest(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    module_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    steps: str | None = None
    severity: DefectSeverity = DefectSeverity.normal
    priority: DefectPriority = DefectPriority.medium
    defect_category: DefectCategory | None = None
    root_cause: str | None = None
    assignee_id: int | None = Field(default=None, ge=1)
    comment: str | None = None
    source_type: DefectSourceType
    source_run_id: int | None = None
    source_case_id: int | None = None
    case_run_id: int | None = None
    functional_run_id: int | None = None


class DefectBatchLinkRequest(BaseModel):
    case_run_ids: list[int] = Field(min_length=1)
    external_key: str | None = None
    defect_id: int | None = None


class DefectOut(BaseModel):
    id: int
    defect_code: str | None = None
    title: str
    severity: DefectSeverity
    priority: DefectPriority
    status: DefectStatus
    defect_category: DefectCategory
    external_key: str | None = None
