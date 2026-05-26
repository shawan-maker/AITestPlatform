import asyncio
from datetime import datetime, timezone

from service.core.enums import RunStatus, SuiteCaseType, TaskSuiteType
from service.core.exceptions import AppException
from service.test_execution.models import TestSuiteRun, TestTaskRun
from service.test_execution.run.run_lock import check_suite_not_running, check_task_not_running_api
from service.test_execution.run.schemas import TriggerRunOut
from service.test_execution.run.suite_runner import SuiteRunner
from service.test_execution.run.task_runner import TaskRunner
from service.test_execution.shared.env_snapshot_helper import create_env_snapshot
from service.test_management.models import TaskSuiteRelation, TestSuite, TestTask
from service.test_management.permissions import ensure_tm_editor
from service.user.models import User


class TriggerService:
    @classmethod
    async def trigger_suite(cls, user: User, suite_id: int) -> TriggerRunOut:
        suite = await TestSuite.get_or_none(id=suite_id)
        if suite is None:
            raise AppException("套件不存在", 404)
        if suite.type == TaskSuiteType.ui:
            raise AppException("UI 套件执行暂未实现", 501)
        await ensure_tm_editor(suite.project_id, user)
        if suite.environment_id is None:
            raise AppException("套件未配置测试环境", 400)
        await check_suite_not_running(suite_id)

        total_cases = await SuiteCaseRelation.filter(
            suite_id=suite_id, case_type=SuiteCaseType.api
        ).count()
        snap = await create_env_snapshot(suite.environment_id, created_by_id=user.id)
        suite_run = await TestSuiteRun.create(
            suite_id=suite_id,
            environment_id=suite.environment_id,
            env_snapshot_id=snap.id,
            triggered_by_id=user.id,
            status=RunStatus.running,
            total_cases=total_cases,
            start_time=datetime.now(timezone.utc),
        )
        asyncio.create_task(SuiteRunner.run(suite_run.id))
        return TriggerRunOut(suite_run_id=suite_run.id, status=RunStatus.running)

    @classmethod
    async def trigger_api_task(cls, user: User, task_id: int) -> TriggerRunOut:
        task = await TestTask.get_or_none(id=task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        if task.type == TaskSuiteType.functional:
            raise AppException("功能任务请使用手工执行接口", 400)
        if task.type == TaskSuiteType.ui:
            raise AppException("UI 任务执行暂未实现", 501)
        await ensure_tm_editor(task.project_id, user)
        if task.environment_id is None:
            raise AppException("任务未配置测试环境", 400)
        await check_task_not_running_api(task_id)

        total_cases = await TaskRunner.count_task_cases(task)
        total_suites = await TaskSuiteRelation.filter(task_id=task_id).count()
        snap = await create_env_snapshot(task.environment_id, created_by_id=user.id)
        task_run = await TestTaskRun.create(
            task_id=task_id,
            environment_id=task.environment_id,
            env_snapshot_id=snap.id,
            triggered_by_id=user.id,
            status=RunStatus.running,
            total_suites=total_suites,
            total_cases=total_cases,
            start_time=datetime.now(timezone.utc),
        )
        asyncio.create_task(TaskRunner.run_api_task(task_run.id))
        return TriggerRunOut(task_run_id=task_run.id, status=RunStatus.running)
