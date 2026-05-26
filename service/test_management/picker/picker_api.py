from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.response import success
from service.test_management.picker.picker_service import PickerService
from service.test_management.picker.schemas import (
    ApiCasePickerQuery,
    FunctionalCasePickerQuery,
    SuitePickerQuery,
)
from service.user.models import User

router = APIRouter(prefix="/pickers", tags=["测试管理-选用"])


@router.get("/api-cases", summary="选用 API 用例（仅 ready）")
async def list_api_cases_picker(
    project_id: int = Query(..., ge=1),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    query = ApiCasePickerQuery(project_id=project_id, q=q, page=page, page_size=page_size)
    data = await PickerService.list_api_cases(user, query)
    return success(data=data)


@router.get("/functional-cases", summary="选用功能用例")
async def list_functional_cases_picker(
    project_id: int = Query(..., ge=1),
    q: str | None = Query(default=None),
    module_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    query = FunctionalCasePickerQuery(
        project_id=project_id, q=q, module_id=module_id, page=page, page_size=page_size
    )
    data = await PickerService.list_functional_cases(user, query)
    return success(data=data)


@router.get("/suites", summary="选用测试套件")
async def list_suites_picker(
    project_id: int = Query(..., ge=1),
    type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    from service.core.enums import TaskSuiteType

    query = SuitePickerQuery(
        project_id=project_id,
        type=TaskSuiteType(type) if type else None,
        q=q,
        page=page,
        page_size=page_size,
    )
    data = await PickerService.list_suites(user, query)
    return success(data=data)
