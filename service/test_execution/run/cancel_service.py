"""测试执行模块 - run/cancel_service

业务逻辑服务
"""
from service.core.enums import RunStatus
from service.core.exceptions import AppException
from service.test_execution.models import TestSuiteRun, TestTaskRun
from service.test_execution.run.run_lock import request_cancel
from service.test_management.permissions import ensure_tm_editor


class CancelService:
    @classmethod
    async def cancel(cls, user, run_id: int) -> None:
        suite_run = await TestSuiteRun.get_or_none(id=run_id)
        if suite_run is not None:
            suite = await suite_run.suite
            await ensure_tm_editor(suite.project_id, user)
            if suite_run.status != RunStatus.running:
                raise AppException("执行已结束，无法停止", 400)
            request_cancel(run_id)
            suite_run.status = RunStatus.cancelled
            await suite_run.save(update_fields=["status", "updated_at"])
            return

        task_run = await TestTaskRun.get_or_none(id=run_id)
        if task_run is not None:
            task = await task_run.task
            await ensure_tm_editor(task.project_id, user)
            if task_run.status != RunStatus.running:
                raise AppException("执行已结束，无法停止", 400)
            request_cancel(run_id)
            task_run.status = RunStatus.cancelled
            await task_run.save(update_fields=["status", "updated_at"])
            return

        raise AppException("运行记录不存在", 404)
