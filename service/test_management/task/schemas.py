"""测试管理模块 - task/schemas

请求/响应 Schema 定义
"""
from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import CaseCategory, RunMode, RunStatus, TaskSuiteType
from service.core.pagination import Paginated, PaginationParams
from service.test_management.shared.schemas_common import LastRunBrief


class TaskListQuery(PaginationParams):
    """任务列表查询query"""
    project_id: int = Field(ge=1)
    q: str | None = None
    status: RunStatus | None = None
    type: TaskSuiteType | None = None
    result: str | None = None
    triggered_by: str | None = None


class TaskCaseItemIn(BaseModel):
    """任务用例itemin"""
    case_id: int = Field(ge=1)


class TaskCreateRequest(BaseModel):
    """任务创建请求"""
    project_id: int = Field(ge=1)
    task_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: TaskSuiteType
    module_id: int | None = None
    environment_id: int | None = None
    run_mode: RunMode | None = None


class TaskUpdateRequest(BaseModel):
    """任务更新请求"""
    task_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    module_id: int | None = None
    environment_id: int | None = None
    run_mode: RunMode | None = None


class TaskOut(BaseModel):
    """任务out"""
    id: int
    project_id: int
    task_name: str
    description: str | None
    type: TaskSuiteType
    module_id: int | None
    environment_id: int | None
    environment_name: str | None = None
    run_mode: RunMode | None
    case_count: int = 0
    last_run: LastRunBrief
    created_at: datetime
    updated_at: datetime


class TaskSuiteBrief(BaseModel):
    """任务套件brief"""
    id: int
    suite_id: int
    suite_name: str
    suite_order: int
    case_count: int = 0


class TaskDetailOut(TaskOut):
    """任务detailout"""
    suites: list[TaskSuiteBrief] = []


class PaginatedTasks(Paginated[TaskOut]):
    """paginatedtasks"""
    pass


class TaskSuiteRelationOut(BaseModel):
    """任务套件关联out"""
    id: int
    suite_id: int
    suite_name: str
    suite_order: int
    case_count: int = 0


class PaginatedTaskSuites(Paginated[TaskSuiteRelationOut]):
    """paginated任务suites"""
    pass


class TaskSuiteReplaceRequest(BaseModel):
    """任务套件replace请求"""
    suite_ids: list[int] = Field(min_length=0)


class TaskSuiteBatchRemoveRequest(BaseModel):
    """任务套件批量操作移除请求"""
    suite_ids: list[int] = Field(min_length=1)


class TaskSuiteReorderRequest(BaseModel):
    """任务套件reorder请求"""
    ordered_suite_ids: list[int] = Field(min_length=1)


class TaskCaseRelationOut(BaseModel):
    """任务用例关联out"""
    id: int
    case_id: int
    case_order: int
    case_name: str | None = None
    case_no: str | None = None
    priority: int | None = None
    case_category: CaseCategory | None = None
    catalog_id: int | None = None
    module_id: int | None = None
    module_name: str | None = None
    exec_result: str | None = None
    defect_code: str | None = None
    triggered_by_name: str | None = None
    exec_time: datetime | None = None


class PaginatedTaskCases(Paginated[TaskCaseRelationOut]):
    """paginated任务cases"""
    pass


class TaskCaseReplaceRequest(BaseModel):
    """任务用例replace请求"""
    case_ids: list[int]


class TaskCaseBatchRemoveRequest(BaseModel):
    """任务用例批量操作移除请求"""
    case_ids: list[int] = Field(min_length=1)


class TaskCaseReorderRequest(BaseModel):
    """任务用例reorder请求"""
    ordered_case_ids: list[int] = Field(min_length=1)


class TaskCaseTreeNode(BaseModel):
    """任务用例treenode"""
    id: int
    name: str
    level: int
    parent_id: int | None
    cases: list[TaskCaseRelationOut] = []
    children: list["TaskCaseTreeNode"] = []


TaskCaseTreeNode.model_rebuild()


class TaskBatchDeleteRequest(BaseModel):
    """任务批量操作删除请求"""
    task_ids: list[int] = Field(..., min_length=1, max_length=50)


class TaskBatchDeleteFailure(BaseModel):
    """任务批量操作删除failure"""
    task_id: int
    message: str


class TaskBatchDeleteResult(BaseModel):
    """任务批量操作删除结果"""
    deleted_ids: list[int]
    failures: list[TaskBatchDeleteFailure]
