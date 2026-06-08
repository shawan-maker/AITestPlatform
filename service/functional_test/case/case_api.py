from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from service.core.deps import get_current_active_user
from service.core.response import success
from service.functional_test.case.case_service import CaseService
from service.functional_test.case.export_service import ExportService
from service.functional_test.case.schemas import (
    CaseBatchDeleteRequest,
    CaseBatchUpdateRequest,
    CaseCreateRequest,
    CaseListQuery,
    CaseReorderRequest,
    CaseUpdateRequest,
)
from service.user.models import User

router = APIRouter(tags=["功能测试-用例"])


def get_case_list_query(
    project_id: int = Query(..., ge=1),
    catalog_id: int | None = Query(None, ge=1),
    case_name: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CaseListQuery:
    return CaseListQuery(
        project_id=project_id,
        catalog_id=catalog_id,
        case_name=case_name,
        page=page,
        page_size=page_size,
    )


@router.get("/cases", summary="功能用例列表")
async def list_cases(
    query: CaseListQuery = Depends(get_case_list_query),
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.list_cases(user, query)
    return success(data=data)


@router.get("/cases/export", summary="导出功能用例 CSV")
async def export_cases(
    project_id: int = Query(..., ge=1),
    catalog_id: int | None = Query(None, ge=1),
    user: User = Depends(get_current_active_user),
):
    filename, content = await ExportService.export_csv(user, project_id, catalog_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cases/{case_id}", summary="功能用例详情")
async def get_case(
    case_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.get_detail(user, case_id)
    # 调试代码：检查返回的JSON响应格式
    import json
    print(f"[DEBUG] get_case response type: {type(data)}")
    print(f"[DEBUG] get_case response: {json.dumps(data.model_dump() if hasattr(data, 'model_dump') else data, ensure_ascii=False, default=str)}")
    return success(data=data)


@router.post("/cases", summary="手工新建功能用例")
async def create_case(
    body: CaseCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.create(user, body)
    return success(data=data, message="用例创建成功")


@router.patch("/cases/{case_id}", summary="编辑功能用例")
async def update_case(
    case_id: int,
    body: CaseUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.update(user, case_id, body)
    return success(data=data, message="用例更新成功")


@router.delete("/cases/{case_id}", summary="删除功能用例")
async def delete_case(
    case_id: int,
    user: User = Depends(get_current_active_user),
):
    await CaseService.delete(user, case_id)
    return success(message="用例删除成功")


@router.post("/cases/{case_id}/copy", summary="复制功能用例")
async def copy_case(
    case_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.copy(user, case_id)
    return success(data=data, message="用例复制成功")


@router.post("/cases/reorder", summary="同目录内用例排序")
async def reorder_cases(
    body: CaseReorderRequest,
    user: User = Depends(get_current_active_user),
):
    await CaseService.reorder(user, body)
    return success(message="排序更新成功")


@router.post("/cases/batch-update", summary="批量编辑用例")
async def batch_update_cases(
    body: CaseBatchUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.batch_update(user, body)
    return success(data=data, message="批量更新完成")


@router.post("/cases/batch-delete", summary="批量删除用例")
async def batch_delete_cases(
    body: CaseBatchDeleteRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.batch_delete(user, body)
    return success(data=data, message="批量删除完成")
