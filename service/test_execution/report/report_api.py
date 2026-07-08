"""测试执行模块 - report/report_api

API 路由端点
"""
from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user
from service.core.response import success
from service.test_execution.report.report_service import ReportService
from service.user.models import User

router = APIRouter(prefix="/runs", tags=["测试执行-报告"])


@router.get("/suite-runs/{run_id}/report", summary="套件执行报告")
async def get_suite_report(
    run_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ReportService.get_suite_report(user, run_id)
    return success(data=data)


@router.get("/task-runs/{run_id}/report", summary="任务执行报告")
async def get_task_report(
    run_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ReportService.get_task_report(user, run_id)
    return success(data=data)


@router.get("/case-runs/{case_run_id}", summary="API 用例运行日志详情")
async def get_case_run_log(
    case_run_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ReportService.get_case_run_log(user, case_run_id)
    return success(data=data)
