"""测试执行模块 - run/progress_service

业务逻辑服务
"""
from service.core.enums import RunStatus
from service.core.exceptions import AppException
from service.test_execution.models import TestSuiteRun, TestTaskRun
from service.test_execution.run.schemas import ProgressOut, SuiteProgressOut, TaskProgressOut
from service.test_management.permissions import ensure_tm_viewer


class ProgressService:
    @classmethod
    def _percent(cls, finished: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return round(min(finished / total * 100, 100.0), 1)

    @classmethod
    async def get_suite_progress(cls, user, run_id: int) -> SuiteProgressOut:
        suite_run = await TestSuiteRun.get_or_none(id=run_id)
        if suite_run is None:
            raise AppException("套件运行记录不存在", 404)
        suite = await suite_run.suite
        await ensure_tm_viewer(suite.project_id, user)
        finished = (
            suite_run.passed_cases
            + suite_run.failed_cases
            + suite_run.error_cases
            + suite_run.skipped_cases
        )
        return SuiteProgressOut(
            finished=finished,
            total=suite_run.total_cases,
            status=suite_run.status,
            percent=cls._percent(finished, suite_run.total_cases),
        )

    @classmethod
    async def get_task_progress(cls, user, run_id: int) -> TaskProgressOut:
        task_run = await TestTaskRun.get_or_none(id=run_id)
        if task_run is None:
            raise AppException("任务运行记录不存在", 404)
        task = await task_run.task
        await ensure_tm_viewer(task.project_id, user)
        finished = (
            task_run.passed_cases
            + task_run.failed_cases
            + task_run.error_cases
            + task_run.skipped_cases
        )
        suite_runs = await TestSuiteRun.filter(run_task_id=run_id).all()
        suite_progress = [
            {
                "suite_run_id": sr.id,
                "suite_id": sr.suite_id,
                "finished": sr.passed_cases + sr.failed_cases + sr.error_cases + sr.skipped_cases,
                "total": sr.total_cases,
                "status": sr.status.value if isinstance(sr.status, RunStatus) else sr.status,
                "percent": cls._percent(
                    sr.passed_cases + sr.failed_cases + sr.error_cases + sr.skipped_cases,
                    sr.total_cases,
                ),
            }
            for sr in suite_runs
        ]
        return TaskProgressOut(
            finished=finished,
            total=task_run.total_cases,
            status=task_run.status,
            percent=cls._percent(finished, task_run.total_cases),
            suite_progress=suite_progress,
        )
