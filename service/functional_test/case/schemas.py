"""用例目录、用例与 AI 生成 Pydantic 模型（请求/响应）。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from service.core.enums import (
    CaseCategory,
    FunctionalCaseStatus,
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
    """目录创建请求"""
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int | None = Field(default=None, ge=1)


class CatalogUpdateRequest(BaseModel):
    """目录更新请求"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = None


class CatalogMoveRequest(BaseModel):
    """目录移动请求"""
    parent_id: int | None = Field(default=None, ge=0, description="0 表示移到根级")
    sort_order: int | None = Field(default=None, ge=0)


class CatalogOut(BaseModel):
    """目录out"""
    id: int
    project_id: int
    parent_id: int | None
    name: str
    level: int
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CatalogTreeNode(CatalogOut):
    """目录treenode"""
    case_count: int = 0
    children: list["CatalogTreeNode"] = Field(default_factory=list)


class CaseListQuery(BaseModel):
    """用例列表查询query"""
    project_id: int = Field(..., ge=1)
    catalog_id: int | None = Field(default=None)
    case_name: str | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    case_category: CaseCategory | None = None
    sort_field: str | None = None
    sort_order: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CaseCreateRequest(BaseModel):
    """用例创建请求"""
    project_id: int = Field(..., ge=1)
    catalog_id: int = Field(..., ge=1)
    case_name: str = Field(..., min_length=1, max_length=255)
    module_id: int | None = Field(default=None, ge=1)
    priority: int = Field(default=3, ge=1, le=4)
    dimension: str | None = Field(default=None, max_length=100)
    case_category: CaseCategory = CaseCategory.functional
    preconditions: str | None = None
    test_steps: str | None = None
    test_data: str | None = None
    expected_result: str | None = None


class CaseUpdateRequest(BaseModel):
    """用例更新请求"""
    catalog_id: int | None = Field(default=None, ge=1)
    case_name: str | None = Field(default=None, min_length=1, max_length=255)
    module_id: int | None = Field(default=None, ge=1)
    priority: int | None = Field(default=None, ge=1, le=4)
    dimension: str | None = Field(default=None, max_length=100)
    case_category: CaseCategory | None = None
    status: FunctionalCaseStatus | None = None
    preconditions: str | None = None
    test_steps: str | None = None
    test_data: str | None = None
    expected_result: str | None = None
    test_point_summary: str | None = None


class TestPointBrief(BaseModel):
    """测试pointbrief"""
    id: int
    type: str
    dimension: str
    test_point: str
    source: SourceType


class CaseBrief(BaseModel):
    """用例brief"""
    id: int
    project_id: int
    catalog_id: int | None
    catalog_name: str | None
    case_name: str
    case_no: str | None
    priority: int
    dimension: str | None
    case_category: CaseCategory
    status: FunctionalCaseStatus
    source: SourceType
    sort_order: int
    module_name: str | None
    created_by_username: str | None
    updated_by_username: str | None
    created_at: datetime
    updated_at: datetime


class CaseDetail(CaseBrief):
    """用例detail"""
    module_id: int | None
    preconditions: str | None
    test_steps: str | None
    test_data: str | None
    expected_result: str | None
    test_point: str | None


class CaseReorderRequest(BaseModel):
    """用例reorder请求"""
    catalog_id: int | None = Field(default=None, ge=1)
    ordered_ids: list[int] = Field(..., min_length=1)


class CaseBatchUpdateRequest(BaseModel):
    """用例批量操作更新请求"""
    case_ids: list[int] = Field(..., min_length=1)
    case_category: CaseCategory | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    status: FunctionalCaseStatus | None = None
    catalog_id: int | None = Field(default=None, ge=1)
    module_id: int | None = Field(default=None, ge=1)
    preconditions: str | None = None
    test_steps: str | None = None
    test_data: str | None = None
    expected_result: str | None = None


class CaseBatchDeleteRequest(BaseModel):
    """用例批量操作删除请求"""
    case_ids: list[int] = Field(..., min_length=1)


class CaseBatchMoveRequest(BaseModel):
    """用例批量操作移动请求"""
    case_ids: list[int] = Field(..., min_length=1)
    target_catalog_id: int = Field(..., ge=1)


class CaseBatchCopyRequest(BaseModel):
    """用例批量操作复制请求"""
    case_ids: list[int] = Field(..., min_length=1)
    target_catalog_id: int = Field(..., ge=1)


class BatchOperationFailure(BaseModel):
    """批量操作operationfailure"""
    case_id: int
    reason: str


class CaseBatchResult(BaseModel):
    """用例批量操作结果"""
    success_count: int
    failures: list[BatchOperationFailure] = Field(default_factory=list)


PaginatedCases = Paginated[CaseBrief]


class GenerationSessionCreateRequest(BaseModel):
    """generation会话创建请求"""
    project_id: int = Field(..., ge=1)
    knowledge_document_id: int | None = Field(default=None, ge=1)
    user_prompt: str | None = None
    module_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, max_length=200)


class GenerationSaveRequest(BaseModel):
    """generation保存请求"""
    catalog_id: int = Field(..., ge=1)
    case_indexes: list[int] = Field(..., min_length=1)


class GenerationSaveResult(BaseModel):
    """generation保存结果"""
    created_case_ids: list[int] = Field(default_factory=list)
    created_test_point_ids: list[int] = Field(default_factory=list)
