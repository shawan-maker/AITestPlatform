"""测试执行模块 - run/history_api

API 路由端点
"""
from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.response import success
from service.test_execution.run.history_service import HistoryService
from service.user.models import User

router = APIRouter(prefix="/runs", tags=["测试执行-历史"])


@router.get("/suites/{suite_id}/history", summary="套件执行历史")
async def list_suite_run_history(
    suite_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await HistoryService.list_suite_history(
        user, suite_id, page=page, page_size=page_size
    )
    return success(data=data)


@router.get("/tasks/{task_id}/history", summary="任务执行历史")
async def list_task_run_history(
    task_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await HistoryService.list_task_history(
        user, task_id, page=page, page_size=page_size
    )
    return success(data=data)
