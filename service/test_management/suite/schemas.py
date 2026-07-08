"""测试管理模块 - suite/schemas

请求/响应 Schema 定义
"""
from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import RunMode, RunStatus, TaskSuiteType
from service.core.pagination import Paginated, PaginationParams
from service.test_management.shared.schemas_common import LastRunBrief


class SuiteListQuery(PaginationParams):
    """套件列表查询query"""
    project_id: int = Field(ge=1)
    q: str | None = None
    status: RunStatus | None = None
    type: TaskSuiteType | None = None
    result: str | None = None  # "success" | "fail"
    triggered_by: str | None = None  # username keyword


class SuiteCaseItemIn(BaseModel):
    """套件用例itemin"""
    case_id: int = Field(ge=1)
    use_dependency: bool = True


class SuiteCreateRequest(BaseModel):
    """套件创建请求"""
    project_id: int = Field(ge=1)
    suite_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: TaskSuiteType
    module_id: int | None = None
    environment_id: int | None = None
    run_mode: RunMode = RunMode.serial
    cases: list[SuiteCaseItemIn] | None = None


class SuiteUpdateRequest(BaseModel):
    """套件更新请求"""
    suite_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    module_id: int | None = None
    environment_id: int | None = None
    run_mode: RunMode | None = None


class SuiteOut(BaseModel):
    """套件out"""
    id: int
    project_id: int
    suite_name: str
    description: str | None
    type: TaskSuiteType
    module_id: int | None
    environment_id: int | None
    environment_name: str | None = None
    run_mode: RunMode
    case_count: int = 0
    last_run: LastRunBrief
    created_at: datetime
    updated_at: datetime


class BoundTaskBrief(BaseModel):
    """bound任务brief"""
    id: int
    task_name: str


class SuiteDetailOut(SuiteOut):
    """套件detailout"""
    bound_tasks: list[BoundTaskBrief] = []


class PaginatedSuites(Paginated[SuiteOut]):
    """paginatedsuites"""
    pass


class SuiteCaseRelationOut(BaseModel):
    """套件用例关联out"""
    id: int
    case_id: int
    case_order: int
    use_dependency: bool
    case_name: str | None = None
    interface_id: int | None = None
    interface_name: str | None = None
    interface_path: str | None = None
    interface_method: str | None = None
    exec_status: str | None = None


class PaginatedSuiteCases(Paginated[SuiteCaseRelationOut]):
    """paginated套件cases"""
    pass


class SuiteCaseReplaceRequest(BaseModel):
    """套件用例replace请求"""
    cases: list[SuiteCaseItemIn]


class SuiteCaseAddRequest(BaseModel):
    """套件用例添加请求"""
    cases: list[SuiteCaseItemIn]


class SuiteCaseBatchRemoveRequest(BaseModel):
    """套件用例批量操作移除请求"""
    case_ids: list[int] = Field(min_length=1)


class SuiteCaseReorderRequest(BaseModel):
    """套件用例reorder请求"""
    ordered_case_ids: list[int] = Field(min_length=1)


class SuiteCaseDependencyPatchRequest(BaseModel):
    """套件用例依赖patch请求"""
    case_ids: list[int] = Field(min_length=1)
    use_dependency: bool


class SuiteBatchDeleteRequest(BaseModel):
    """套件批量操作删除请求"""
    suite_ids: list[int] = Field(..., min_length=1, max_length=50)


class SuiteBatchDeleteFailure(BaseModel):
    """套件批量操作删除failure"""
    suite_id: int
    message: str


class SuiteBatchDeleteResult(BaseModel):
    """套件批量操作删除结果"""
    deleted_ids: list[int]
    failures: list[SuiteBatchDeleteFailure]
