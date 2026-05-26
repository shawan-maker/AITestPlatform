from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user
from service.core.response import success
from service.test_execution.run.cancel_service import CancelService
from service.test_execution.run.progress_service import ProgressService
from service.test_execution.run.trigger_service import TriggerService
from service.user.models import User

router = APIRouter(prefix="/runs", tags=["测试执行-运行"])


@router.post("/suites/{suite_id}", summary="触发套件执行")
async def trigger_suite_run(
    suite_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await TriggerService.trigger_suite(user, suite_id)
    return success(data=data, message="套件执行已启动")


@router.post("/tasks/{task_id}", summary="触发 API/UI 任务执行")
async def trigger_task_run(
    task_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await TriggerService.trigger_api_task(user, task_id)
    return success(data=data, message="任务执行已启动")


@router.post("/{run_id}/cancel", summary="停止执行")
async def cancel_run(
    run_id: int,
    user: User = Depends(get_current_active_user),
):
    await CancelService.cancel(user, run_id)
    return success(message="执行已停止")


@router.get("/suite-runs/{run_id}/progress", summary="套件执行进度")
async def get_suite_progress(
    run_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ProgressService.get_suite_progress(user, run_id)
    return success(data=data)


@router.get("/task-runs/{run_id}/progress", summary="任务执行进度")
async def get_task_progress(
    run_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ProgressService.get_task_progress(user, run_id)
    return success(data=data)
