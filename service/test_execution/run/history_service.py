from service.core.pagination import paginate
from service.test_execution.models import TestSuiteRun, TestTaskRun
from service.test_execution.run.schemas import PaginatedRunHistory, RunHistoryItem
from service.test_management.permissions import ensure_tm_viewer
from service.test_management.models import TestSuite, TestTask
from service.user.models import User


class HistoryService:
    @classmethod
    async def list_suite_history(
        cls, user: User, suite_id: int, *, page: int = 1, page_size: int = 20
    ) -> PaginatedRunHistory:
        suite = await TestSuite.get_or_none(id=suite_id)
        if suite is None:
            from service.core.exceptions import AppException

            raise AppException("套件不存在", 404)
        await ensure_tm_viewer(suite.project_id, user)
        qs = TestSuiteRun.filter(suite_id=suite_id).order_by("-id")
        total, items = await paginate(qs, page, page_size)
        out = []
        for run in items:
            triggered_name = None
            task_name = None
            if run.triggered_by_id:
                from service.user.models import User as UserModel

                u = await UserModel.get_or_none(id=run.triggered_by_id)
                triggered_name = u.username if u else None
            if run.run_task_id:
                task_run = await TestTaskRun.get_or_none(id=run.run_task_id)
                if task_run:
                    task = await TestTask.get_or_none(id=task_run.task_id)
                    task_name = task.task_name if task else None
            out.append(
                RunHistoryItem(
                    id=run.id,
                    status=run.status,
                    total_cases=run.total_cases,
                    passed_cases=run.passed_cases,
                    failed_cases=run.failed_cases,
                    error_cases=run.error_cases,
                    skipped_cases=run.skipped_cases,
                    start_time=run.start_time,
                    end_time=run.end_time,
                    duration_ms=run.duration_ms,
                    triggered_by_name=triggered_name,
                    task_name=task_name,
                )
            )
        return PaginatedRunHistory(total=total, page=page, page_size=page_size, items=out)

    @classmethod
    async def list_task_history(
        cls, user: User, task_id: int, *, page: int = 1, page_size: int = 20
    ) -> PaginatedRunHistory:
        task = await TestTask.get_or_none(id=task_id)
        if task is None:
            from service.core.exceptions import AppException

            raise AppException("任务不存在", 404)
        await ensure_tm_viewer(task.project_id, user)
        qs = TestTaskRun.filter(task_id=task_id).order_by("-id")
        total, items = await paginate(qs, page, page_size)
        out = []
        for run in items:
            triggered_name = None
            if run.triggered_by_id:
                from service.user.models import User as UserModel

                u = await UserModel.get_or_none(id=run.triggered_by_id)
                triggered_name = u.username if u else None
            out.append(
                RunHistoryItem(
                    id=run.id,
                    status=run.status,
                    total_cases=run.total_cases,
                    passed_cases=run.passed_cases,
                    failed_cases=run.failed_cases,
                    error_cases=run.error_cases,
                    skipped_cases=run.skipped_cases,
                    start_time=run.start_time,
                    end_time=run.end_time,
                    duration_ms=run.duration_ms,
                    triggered_by_name=triggered_name,
                    task_name=task.task_name,
                )
            )
        return PaginatedRunHistory(total=total, page=page, page_size=page_size, items=out)
