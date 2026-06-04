"""用例目录、用例与 AI 生成 Pydantic 模型（请求/响应）。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from service.core.enums import (
    FunctionalCaseStatus,
    FunctionalCaseType,
    FunctionalExecResult,
    SessionStatus,
    SourceType,
)
from service.core.pagination import Paginated
from service.ai_generation.session_schemas import (
    AIGenerationPreviewUpdateRequest,
    AIGenerationSessionOut,
)

GenerationPreviewUpdateRequest = AIGenerationPreviewUpdateRequest
GenerationSessionOut = AIGenerationSessionOut


class CatalogCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int | None = Field(default=None, ge=1)


class CatalogUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = None


class CatalogMoveRequest(BaseModel):
    parent_id: int | None = Field(default=None, ge=0, description="0 表示移到根级")
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
    case_count: int = 0
    children: list["CatalogTreeNode"] = Field(default_factory=list)


class CaseListQuery(BaseModel):
    project_id: int = Field(..., ge=1)
    catalog_id: int | None = Field(default=None, ge=1)
    case_name: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CaseCreateRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    catalog_id: int = Field(..., ge=1)
    case_name: str = Field(..., min_length=1, max_length=255)
    module_id: int | None = Field(default=None, ge=1)
    requirement_id: int | None = Field(default=None, ge=1)
    priority: int = Field(default=3, ge=1, le=4)
    dimension: str | None = Field(default=None, max_length=100)
    type: FunctionalCaseType = FunctionalCaseType.functional
    preconditions: str | None = None
    test_steps: str | None = None
    test_data: str | None = None
    expected_result: str | None = None


class CaseUpdateRequest(BaseModel):
    catalog_id: int | None = Field(default=None, ge=1)
    case_name: str | None = Field(default=None, min_length=1, max_length=255)
    module_id: int | None = Field(default=None, ge=1)
    requirement_id: int | None = Field(default=None, ge=1)
    priority: int | None = Field(default=None, ge=1, le=4)
    dimension: str | None = Field(default=None, max_length=100)
    type: FunctionalCaseType | None = None
    status: FunctionalCaseStatus | None = None
    exec_result: FunctionalExecResult | None = None
    preconditions: str | None = None
    test_steps: str | None = None
    test_data: str | None = None
    expected_result: str | None = None
    actual_result: str | None = None
    jira_issue_key: str | None = Field(default=None, max_length=50)
    test_point_summary: str | None = None


class TestPointBrief(BaseModel):
    id: int
    type: str
    dimension: str
    test_point: str
    source: SourceType


class CaseBrief(BaseModel):
    id: int
    project_id: int
    catalog_id: int | None
    catalog_name: str | None
    case_name: str
    case_no: str | None
    priority: int
    dimension: str | None
    type: FunctionalCaseType
    status: FunctionalCaseStatus
    exec_result: FunctionalExecResult
    source: SourceType
    sort_order: int
    jira_issue_key: str | None
    created_by_username: str | None
    updated_at: datetime


class CaseDetail(CaseBrief):
    module_id: int | None
    requirement_id: int | None
    preconditions: str | None
    test_steps: str | None
    test_data: str | None
    expected_result: str | None
    actual_result: str | None
    test_point: TestPointBrief | None
    created_at: datetime


class CaseReorderRequest(BaseModel):
    catalog_id: int = Field(..., ge=1)
    ordered_ids: list[int] = Field(..., min_length=1)


class CaseBatchUpdateRequest(BaseModel):
    case_ids: list[int] = Field(..., min_length=1)
    priority: int | None = Field(default=None, ge=1, le=4)
    status: FunctionalCaseStatus | None = None
    exec_result: FunctionalExecResult | None = None
    catalog_id: int | None = Field(default=None, ge=1)
    module_id: int | None = Field(default=None, ge=1)


class CaseBatchDeleteRequest(BaseModel):
    case_ids: list[int] = Field(..., min_length=1)


class BatchOperationFailure(BaseModel):
    case_id: int
    reason: str


class CaseBatchResult(BaseModel):
    success_count: int
    failures: list[BatchOperationFailure] = Field(default_factory=list)


class CaseDeleteBlocked(BaseModel):
    suite_names: list[str]


PaginatedCases = Paginated[CaseBrief]


class GenerationSessionCreateRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    requirement_id: int | None = Field(default=None, ge=1)
    requirement_text: str | None = None
    knowledge_document_id: int | None = Field(default=None, ge=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)


class GenerationSaveRequest(BaseModel):
    catalog_id: int = Field(..., ge=1)
    case_indexes: list[int] = Field(..., min_length=1)
    requirement_id: int | None = Field(default=None, ge=1)


class GenerationSaveResult(BaseModel):
    created_case_ids: list[int]
    created_test_point_ids: list[int]
