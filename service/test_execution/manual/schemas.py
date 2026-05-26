from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import FunctionalExecResult, RunStatus
from service.test_management.task.schemas import TaskCaseTreeNode


class ManualSessionOut(BaseModel):
    task_run_id: int
    status: RunStatus
    resumed: bool


class ManualCaseDetailOut(BaseModel):
    case_id: int
    case_name: str
    preconditions: str | None = None
    test_steps: str | None = None
    expected_result: str | None = None
    exec_result: FunctionalExecResult | None = None
    remark: str | None = None


class ManualRunContextOut(BaseModel):
    task_run_id: int
    task_name: str
    status: RunStatus
    tree: list[TaskCaseTreeNode]


class ManualCaseUpdateRequest(BaseModel):
    exec_result: FunctionalExecResult
    remark: str | None = None
