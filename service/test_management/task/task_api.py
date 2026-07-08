"""测试管理模块 - task/task_api

API 路由端点
"""
from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.response import success
from service.test_management.task.case_relation_service import TaskCaseRelationService
from service.test_management.task.schemas import (
    TaskBatchDeleteRequest,
    TaskCaseBatchRemoveRequest,
    TaskCaseReplaceRequest,
    TaskCaseReorderRequest,
    TaskCreateRequest,
    TaskListQuery,
    TaskSuiteBatchRemoveRequest,
    TaskSuiteReorderRequest,
    TaskSuiteReplaceRequest,
    TaskUpdateRequest,
)
from service.test_management.task.suite_relation_service import SuiteRelationService
from service.test_management.task.task_service import TaskService
from service.user.models import User

router = APIRouter(prefix="/tasks", tags=["测试管理-任务"])


@router.get("", summary="任务列表")
async def list_tasks(
    project_id: int = Query(..., ge=1),
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    result: str | None = Query(default=None),
    triggered_by: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    from service.core.enums import RunStatus, TaskSuiteType

    query = TaskListQuery(
        project_id=project_id,
        q=q,
        status=RunStatus(status) if status else None,
        type=TaskSuiteType(type) if type else None,
        result=result,
        triggered_by=triggered_by,
        page=page,
        page_size=page_size,
    )
    data = await TaskService.list(user, query)
    return success(data=data)


@router.post("", summary="新建任务")
async def create_task(
    body: TaskCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await TaskService.create(user, body)
    return success(data=data, message="任务创建成功")


@router.post("/batch-delete", summary="批量删除任务")
async def batch_delete(
    data: TaskBatchDeleteRequest,
    user: User = Depends(get_current_active_user),
):
    result = await TaskService.batch_delete(user, data)
    return success(data=result)


@router.get("/{task_id}", summary="任务详情")
async def get_task(
    task_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await TaskService.get_detail(user, task_id)
    return success(data=data)


@router.patch("/{task_id}", summary="更新任务")
async def update_task(
    task_id: int,
    body: TaskUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await TaskService.update(user, task_id, body)
    return success(data=data, message="任务更新成功")


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(
    task_id: int,
    user: User = Depends(get_current_active_user),
):
    await TaskService.delete(user, task_id)
    return success(message="任务删除成功")


@router.get("/{task_id}/suites", summary="任务关联套件列表")
async def list_task_suites(
    task_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await SuiteRelationService.list(user, task_id, page=page, page_size=page_size)
    return success(data=data)


@router.put("/{task_id}/suites", summary="全量替换任务关联套件")
async def replace_task_suites(
    task_id: int,
    body: TaskSuiteReplaceRequest,
    user: User = Depends(get_current_active_user),
):
    await SuiteRelationService.replace(user, task_id, body)
    return success(message="关联套件已更新")


@router.post("/{task_id}/suites/reorder", summary="任务套件排序")
async def reorder_task_suites(
    task_id: int,
    body: TaskSuiteReorderRequest,
    user: User = Depends(get_current_active_user),
):
    await SuiteRelationService.reorder(user, task_id, body.ordered_suite_ids)
    return success(message="排序更新成功")


@router.delete("/{task_id}/suites", summary="批量删除任务关联套件")
async def remove_task_suites(
    task_id: int,
    body: TaskSuiteBatchRemoveRequest,
    user: User = Depends(get_current_active_user),
):
    await SuiteRelationService.batch_remove(user, task_id, body)
    return success(message="关联套件已删除")


@router.get("/{task_id}/cases", summary="功能任务关联用例列表")
async def list_task_cases(
    task_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await TaskCaseRelationService.list(user, task_id, page=page, page_size=page_size)
    return success(data=data)


@router.put("/{task_id}/cases", summary="全量替换功能任务关联用例")
async def replace_task_cases(
    task_id: int,
    body: TaskCaseReplaceRequest,
    user: User = Depends(get_current_active_user),
):
    await TaskCaseRelationService.replace(user, task_id, body)
    return success(message="关联用例已更新")


@router.post("/{task_id}/cases/reorder", summary="功能任务用例排序")
async def reorder_task_cases(
    task_id: int,
    body: TaskCaseReorderRequest,
    user: User = Depends(get_current_active_user),
):
    await TaskCaseRelationService.reorder(user, task_id, body.ordered_case_ids)
    return success(message="排序更新成功")


@router.delete("/{task_id}/cases", summary="批量删除功能任务关联用例")
async def remove_task_cases(
    task_id: int,
    body: TaskCaseBatchRemoveRequest,
    user: User = Depends(get_current_active_user),
):
    await TaskCaseRelationService.batch_remove(user, task_id, body)
    return success(message="关联用例已删除")


@router.get("/{task_id}/cases/tree", summary="功能任务用例目录树")
async def get_task_case_tree(
    task_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await TaskCaseRelationService.get_tree(user, task_id)
    return success(data=data)
