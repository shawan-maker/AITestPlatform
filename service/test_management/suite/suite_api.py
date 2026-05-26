from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.response import success
from service.test_management.suite.case_relation_service import CaseRelationService
from service.test_management.suite.schemas import (
    SuiteCaseAddRequest,
    SuiteCaseBatchRemoveRequest,
    SuiteCaseDependencyPatchRequest,
    SuiteCaseReorderRequest,
    SuiteCaseReplaceRequest,
)
from service.test_management.suite.suite_service import SuiteService
from service.test_management.suite.schemas import SuiteCreateRequest, SuiteListQuery, SuiteUpdateRequest
from service.user.models import User

router = APIRouter(prefix="/suites", tags=["测试管理-套件"])


@router.get("", summary="套件列表")
async def list_suites(
    project_id: int = Query(..., ge=1),
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    from service.core.enums import RunStatus, TaskSuiteType

    query = SuiteListQuery(
        project_id=project_id,
        q=q,
        status=RunStatus(status) if status else None,
        type=TaskSuiteType(type) if type else None,
        page=page,
        page_size=page_size,
    )
    data = await SuiteService.list(user, query)
    return success(data=data)


@router.post("", summary="新建套件")
async def create_suite(
    body: SuiteCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await SuiteService.create(user, body)
    return success(data=data, message="套件创建成功")


@router.get("/{suite_id}", summary="套件详情")
async def get_suite(
    suite_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await SuiteService.get_detail(user, suite_id)
    return success(data=data)


@router.patch("/{suite_id}", summary="更新套件")
async def update_suite(
    suite_id: int,
    body: SuiteUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await SuiteService.update(user, suite_id, body)
    return success(data=data, message="套件更新成功")


@router.delete("/{suite_id}", summary="删除套件")
async def delete_suite(
    suite_id: int,
    user: User = Depends(get_current_active_user),
):
    await SuiteService.delete(user, suite_id)
    return success(message="套件删除成功")


@router.get("/{suite_id}/cases", summary="套件关联用例列表")
async def list_suite_cases(
    suite_id: int,
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await CaseRelationService.list(user, suite_id, q=q, page=page, page_size=page_size)
    return success(data=data)


@router.put("/{suite_id}/cases", summary="全量替换套件关联用例")
async def replace_suite_cases(
    suite_id: int,
    body: SuiteCaseReplaceRequest,
    user: User = Depends(get_current_active_user),
):
    await CaseRelationService.replace(user, suite_id, body)
    return success(message="关联用例已更新")


@router.post("/{suite_id}/cases", summary="追加套件关联用例")
async def add_suite_cases(
    suite_id: int,
    body: SuiteCaseAddRequest,
    user: User = Depends(get_current_active_user),
):
    await CaseRelationService.add(user, suite_id, body)
    return success(message="关联用例已追加")


@router.delete("/{suite_id}/cases", summary="批量删除套件关联用例")
async def remove_suite_cases(
    suite_id: int,
    body: SuiteCaseBatchRemoveRequest,
    user: User = Depends(get_current_active_user),
):
    await CaseRelationService.batch_remove(user, suite_id, body)
    return success(message="关联用例已删除")


@router.post("/{suite_id}/cases/reorder", summary="套件用例排序")
async def reorder_suite_cases(
    suite_id: int,
    body: SuiteCaseReorderRequest,
    user: User = Depends(get_current_active_user),
):
    await CaseRelationService.reorder(user, suite_id, body.ordered_case_ids)
    return success(message="排序更新成功")


@router.patch("/{suite_id}/cases/dependency-flags", summary="批量更新依赖开关")
async def patch_suite_case_dependency(
    suite_id: int,
    body: SuiteCaseDependencyPatchRequest,
    user: User = Depends(get_current_active_user),
):
    await CaseRelationService.patch_dependency(user, suite_id, body)
    return success(message="依赖开关已更新")
