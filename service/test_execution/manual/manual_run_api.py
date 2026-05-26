from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user
from service.core.response import success
from service.test_execution.manual.manual_run_service import ManualRunService
from service.test_execution.manual.schemas import ManualCaseUpdateRequest
from service.user.models import User

router = APIRouter(prefix="/runs", tags=["测试执行-手工"])


@router.post("/tasks/{task_id}/manual", summary="打开/恢复手工执行会话")
async def open_manual_session(
    task_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ManualRunService.open_session(user, task_id)
    return success(data=data)


@router.get("/task-runs/{run_id}/manual", summary="手工执行页上下文")
async def get_manual_context(
    run_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ManualRunService.get_context(user, run_id)
    return success(data=data)


@router.get("/task-runs/{run_id}/manual/cases/{case_id}", summary="手工执行用例抽屉")
async def get_manual_case_detail(
    run_id: int,
    case_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ManualRunService.get_case_detail(user, run_id, case_id)
    return success(data=data)


@router.patch("/task-runs/{run_id}/manual/cases/{case_id}", summary="回填手工执行结果")
async def update_manual_case_result(
    run_id: int,
    case_id: int,
    body: ManualCaseUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    await ManualRunService.update_case_result(user, run_id, case_id, body)
    return success(message="执行结果已保存")
