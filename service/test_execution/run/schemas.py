from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from service.core.enums import RunStatus
from service.core.pagination import Paginated, PaginationParams


class TriggerRunOut(BaseModel):
    suite_run_id: int | None = None
    task_run_id: int | None = None
    status: RunStatus


class ProgressOut(BaseModel):
    finished: int
    total: int
    status: RunStatus
    percent: float


class SuiteProgressOut(ProgressOut):
    pass


class TaskProgressOut(ProgressOut):
    suite_progress: list[dict] = []


class RunHistoryItem(BaseModel):
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
    pass


class RunHistoryQuery(PaginationParams):
    pass
