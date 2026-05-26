from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import RunMode, RunStatus, TaskSuiteType
from service.core.pagination import Paginated, PaginationParams
from service.test_management.shared.schemas_common import LastRunBrief


class TaskListQuery(PaginationParams):
    project_id: int = Field(ge=1)
    q: str | None = None
    status: RunStatus | None = None
    type: TaskSuiteType | None = None


class TaskCaseItemIn(BaseModel):
    case_id: int = Field(ge=1)


class TaskCreateRequest(BaseModel):
    project_id: int = Field(ge=1)
    task_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: TaskSuiteType
    module_id: int | None = None
    environment_id: int | None = None
    run_mode: RunMode | None = None


class TaskUpdateRequest(BaseModel):
    task_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    module_id: int | None = None
    environment_id: int | None = None
    run_mode: RunMode | None = None


class TaskOut(BaseModel):
    id: int
    project_id: int
    task_name: str
    description: str | None
    type: TaskSuiteType
    module_id: int | None
    environment_id: int | None
    run_mode: RunMode | None
    case_count: int = 0
    last_run: LastRunBrief
    created_at: datetime
    updated_at: datetime


class TaskSuiteBrief(BaseModel):
    id: int
    suite_id: int
    suite_name: str
    suite_order: int
    case_count: int = 0


class TaskDetailOut(TaskOut):
    suites: list[TaskSuiteBrief] = []


class PaginatedTasks(Paginated[TaskOut]):
    pass


class TaskSuiteRelationOut(BaseModel):
    id: int
    suite_id: int
    suite_name: str
    suite_order: int
    case_count: int = 0


class PaginatedTaskSuites(Paginated[TaskSuiteRelationOut]):
    pass


class TaskSuiteReplaceRequest(BaseModel):
    suite_ids: list[int] = Field(min_length=0)


class TaskSuiteBatchRemoveRequest(BaseModel):
    suite_ids: list[int] = Field(min_length=1)


class TaskSuiteReorderRequest(BaseModel):
    ordered_suite_ids: list[int] = Field(min_length=1)


class TaskCaseRelationOut(BaseModel):
    id: int
    case_id: int
    case_order: int
    case_name: str | None = None
    catalog_id: int | None = None
    module_id: int | None = None


class PaginatedTaskCases(Paginated[TaskCaseRelationOut]):
    pass


class TaskCaseReplaceRequest(BaseModel):
    case_ids: list[int]


class TaskCaseBatchRemoveRequest(BaseModel):
    case_ids: list[int] = Field(min_length=1)


class TaskCaseReorderRequest(BaseModel):
    ordered_case_ids: list[int] = Field(min_length=1)


class TaskCaseTreeNode(BaseModel):
    id: int
    name: str
    level: int
    parent_id: int | None
    cases: list[TaskCaseRelationOut] = []
    children: list["TaskCaseTreeNode"] = []


TaskCaseTreeNode.model_rebuild()
