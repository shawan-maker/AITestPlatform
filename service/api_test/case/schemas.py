"""接口测试模块 - case/schemas

请求/响应 Schema 定义
"""
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
    locale: str | None = Field(default=None, description="前端 i18n locale，如 en-US / zh-CN")


class BaseCasePreviewItem(BaseModel):
    """基础用例previewitem"""
    index: int
    name: str
    steps: list[str]
    dependencies: list[str]
    expected: list[str]


class GeneratePreviewResult(BaseModel):
    """生成preview结果"""
    session_id: int
    base_cases: list[BaseCasePreviewItem]


class GenerateConfirmRequest(BaseModel):
    """生成confirm请求"""
    session_id: int = Field(..., ge=1)
    selected_indexes: list[int] = Field(..., min_length=1)
    environment_id: int | None = Field(default=None, ge=1)
    edited_base_cases: list[dict] | None = Field(default=None, description="编辑后的基础用例（可选）")


class GenerateConfirmResult(BaseModel):
    """生成confirm结果"""
    created_base_case_ids: list[int]
    created_case_ids: list[int]
    run_errors: list[str] = Field(default_factory=list)


class PreviewFromDocRequest(BaseModel):
    """previewfrom文档请求"""
    project_id: int = Field(..., ge=1)
    api_doc_text: str = Field(..., min_length=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)
    locale: str | None = Field(default=None, description="前端 i18n locale，如 en-US / zh-CN")


class ApiSessionPreviewUpdateRequest(BaseModel):
    """API会话preview更新请求"""
    output_payload: dict[str, Any]


class ApiConfirmRequest(BaseModel):
    """APIconfirm请求"""
    session_id: int = Field(..., ge=1)
    selected_indexes: list[int] = Field(..., min_length=1)
    environment_id: int | None = Field(default=None, ge=1)
    catalog_id: int | None = Field(default=None, ge=1)
    interface_id: int | None = Field(default=None, ge=1)
    edited_base_cases: list[dict] | None = Field(default=None)


class ApiConfirmResult(BaseModel):
    """APIconfirm结果"""
    created_base_case_ids: list[int]
    created_case_ids: list[int]
    run_errors: list[str] = Field(default_factory=list)
    created_interface_id: int | None = None


class CaseUpdateRequest(BaseModel):
    """用例更新请求"""
    title: str | None = Field(default=None, min_length=1, max_length=255)
    case_payload: dict[str, Any] | None = None


class CaseOut(BaseModel):
    """用例out"""
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
    """用例批量操作删除请求"""
    case_ids: list[int] = Field(..., min_length=1)


class CaseReuseRequest(BaseModel):
    """用例reuse请求"""
    source_case_ids: list[int] = Field(..., min_length=1)
    target_interface_id: int = Field(..., ge=1)
    target_case_kind: ApiCaseKind


class CaseReuseResult(BaseModel):
    """用例reuse结果"""
    created_count: int
    created_ids: list[int]
    failures: list[dict] = []


class CaseDebugRunRequest(BaseModel):
    """用例调试执行请求"""
    environment_id: int = Field(..., ge=1)


class RunRecordOut(BaseModel):
    """执行recordout"""
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
