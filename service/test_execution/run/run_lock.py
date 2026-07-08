"""测试执行模块 - run/run_lock

run lock
"""
from service.core.enums import RunStatus
from service.core.exceptions import AppException
from service.test_execution.models import TestSuiteRun, TestTaskRun
from service.test_management.models import TestSuite, TestTask

_cancel_flags: set[int] = set()


def request_cancel(run_id: int) -> None:
    _cancel_flags.add(run_id)


def is_cancel_requested(run_id: int) -> bool:
    return run_id in _cancel_flags


def clear_cancel_flag(run_id: int) -> None:
    _cancel_flags.discard(run_id)


async def assert_no_running_for_suite(suite_id: int) -> None:
    if await TestSuiteRun.filter(suite_id=suite_id, status=RunStatus.running).exists():
        raise AppException("套件存在进行中的执行，请先停止后再删除", 409)


async def assert_no_running_for_task(task_id: int) -> None:
    if await TestTaskRun.filter(task_id=task_id, status=RunStatus.running).exists():
        raise AppException("任务存在进行中的执行，请先停止后再删除", 409)


async def check_suite_not_running(suite_id: int) -> None:
    if await TestSuiteRun.filter(suite_id=suite_id, status=RunStatus.running).exists():
        raise AppException("套件正在执行中，请等待完成或停止后再试", 409)


async def check_task_not_running_api(task_id: int) -> None:
    task = await TestTask.get_or_none(id=task_id)
    if task is None:
        raise AppException("任务不存在", 404)
    if task.type.value == "functional":
        return
    if await TestTaskRun.filter(task_id=task_id, status=RunStatus.running).exists():
        raise AppException("任务正在执行中，请等待完成或停止后再试", 409)


async def get_running_task_run(task_id: int) -> TestTaskRun | None:
    return await TestTaskRun.filter(task_id=task_id, status=RunStatus.running).first()
