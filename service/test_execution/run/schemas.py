"""测试执行模块 - run/schemas

请求/响应 Schema 定义
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from service.core.enums import RunStatus
from service.core.pagination import Paginated, PaginationParams


class TriggerRunOut(BaseModel):
    """触发执行out"""
    suite_run_id: int | None = None
    task_run_id: int | None = None
    status: RunStatus


class ProgressOut(BaseModel):
    """进度out"""
    finished: int
    total: int
    status: RunStatus
    percent: float


class SuiteProgressOut(ProgressOut):
    """套件进度out"""
    pass


class TaskProgressOut(ProgressOut):
    """任务进度out"""
    suite_progress: list[dict] = []


class RunHistoryItem(BaseModel):
    """执行历史item"""
    id: int
    status: RunStatus
    total_cases: int
    passed_cases: int
    failed_cases: int
    error_cases: int
    skipped_cases: int
    start_time: datetime | None
    end_time: datetime | None
    duration_ms: int | None
    triggered_by_name: str | None = None
    task_name: str | None = None


class PaginatedRunHistory(Paginated[RunHistoryItem]):
    """paginated执行历史"""
    pass


class RunHistoryQuery(PaginationParams):
    """执行历史query"""
    pass
