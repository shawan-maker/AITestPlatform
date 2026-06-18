from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from service.core.enums import ApiCaseKind, ExecStatus, ReviewStatus, SessionStatus
from service.core.pagination import Paginated
from service.ai_generation.session_schemas import (
    AIGenerationPreviewUpdateRequest,
    AIGenerationSessionOut,
)

ApiGenerationSessionOut = AIGenerationSessionOut
ApiSessionPreviewUpdateRequest = AIGenerationPreviewUpdateRequest


class GenerationStatusOut(BaseModel):
    """v3新增: AI预执行进度轮询响应"""
    session_id: int
    status: str  # running | success | failed | cancelled
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: dict | None = None  # {total, completed, items[]}
    error_message: str | None = None
    confirm_result: dict | None = None  # {created_base_case_ids, created_case_ids, run_errors, created_interface_id}
    base_cases: list["BaseCasePreviewItem"] | None = None  # 预览完成时返回的用例列表


class GeneratePreviewRequest(BaseModel):
    """v2修订: 移除user_prompt参数，直接AI生成（请求体可为空）"""
    environment_id: int | None = Field(default=None, ge=1)


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
    environment_id: int | None = Field(default=None, ge=1)
    edited_base_cases: list[dict] | None = Field(default=None, description="编辑后的基础用例（可选）")


class GenerateConfirmResult(BaseModel):
    created_base_case_ids: list[int]
    created_case_ids: list[int]
    run_errors: list[str] = Field(default_factory=list)


class PreviewFromDocRequest(BaseModel):
    project_id: int = Field(..., ge=1)
    api_doc_text: str = Field(..., min_length=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)


class ApiSessionPreviewUpdateRequest(BaseModel):
    output_payload: dict[str, Any]


class ApiConfirmRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    selected_indexes: list[int] = Field(..., min_length=1)
    environment_id: int | None = Field(default=None, ge=1)
    catalog_id: int | None = Field(default=None, ge=1)
    interface_id: int | None = Field(default=None, ge=1)
    edited_base_cases: list[dict] | None = Field(default=None)


class ApiConfirmResult(BaseModel):
    created_base_case_ids: list[int]
    created_case_ids: list[int]
    run_errors: list[str] = Field(default_factory=list)
    created_interface_id: int | None = None


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
    updated_by_name: str | None = None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CaseBatchDeleteRequest(BaseModel):
    case_ids: list[int] = Field(..., min_length=1)


class CaseReuseRequest(BaseModel):
    source_case_ids: list[int] = Field(..., min_length=1)
    target_interface_id: int = Field(..., ge=1)
    target_case_kind: ApiCaseKind


class CaseReuseResult(BaseModel):
    created_count: int
    created_ids: list[int]
    failures: list[dict] = []


class CaseDebugRunRequest(BaseModel):
    environment_id: int = Field(..., ge=1)


class RunRecordOut(BaseModel):
    id: int
    case_name: str
    interface_name: str | None = None
    status: str
    run_type: str
    duration_ms: int | None
    error_message: str | None
    created_at: datetime
    triggered_by_username: str | None = None
    api_requests_info: dict[str, Any] | None = None  # 调试执行的详细结果


PaginatedCases = Paginated[CaseOut]
PaginatedRunRecords = Paginated[RunRecordOut]
