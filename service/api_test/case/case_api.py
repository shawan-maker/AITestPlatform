from fastapi import APIRouter, Depends, Query

from service.api_test.case.case_service import CaseService
from service.api_test.case.generation_service import ApiCaseGenerationService
from service.api_test.case.schemas import (
    ApiSessionPreviewUpdateRequest,
    CaseBatchDeleteRequest,
    CaseDebugRunRequest,
    CaseReuseRequest,
    CaseUpdateRequest,
    GenerationStatusOut,
    GenerateConfirmRequest,
    GeneratePreviewRequest,
    PreviewFromDocRequest,
)
from service.core.deps import get_current_active_user
from service.core.enums import ApiCaseKind
from service.core.response import success
from service.user.models import User

router = APIRouter(tags=["接口测试-用例"])


@router.post(
    "/interfaces/{interface_id}/cases/generate-preview",
    summary="生成预览",
    deprecated=True,
    tags=["legacy-case-generation"],
)
async def generate_preview(
    interface_id: int,
    body: GeneratePreviewRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiCaseGenerationService.preview(user, interface_id, body)
    return success(data=data)


@router.post(
    "/case-generation/preview-from-doc",
    summary="从文档生成预览",
    deprecated=True,
    tags=["legacy-case-generation"],
)
async def preview_from_doc(
    body: PreviewFromDocRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiCaseGenerationService.preview_from_doc(user, body)
    return success(data=data)


@router.get(
    "/case-generation/sessions/{session_id}",
    summary="查询生成会话",
    deprecated=True,
    tags=["legacy-case-generation"],
)
async def get_generation_session(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ApiCaseGenerationService.get_session(user, session_id)
    return success(data=data)


@router.patch(
    "/case-generation/sessions/{session_id}/preview",
    summary="编辑生成预览",
    deprecated=True,
    tags=["legacy-case-generation"],
)
async def update_generation_preview(
    session_id: int,
    body: ApiSessionPreviewUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiCaseGenerationService.update_preview(user, session_id, body)
    return success(data=data, message="预览已更新")


@router.post(
    "/interfaces/{interface_id}/cases/confirm",
    summary="确认生成并入库",
    deprecated=True,
    tags=["legacy-case-generation"],
)
async def generate_confirm(
    interface_id: int,
    body: GenerateConfirmRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiCaseGenerationService.confirm(user, interface_id, body)
    return success(data=data, message="用例生成完成")


@router.get("/interfaces/{interface_id}/cases", summary="接口用例列表")
async def list_cases(
    interface_id: int,
    case_kind: ApiCaseKind | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.list_by_interface(
        user, interface_id, case_kind=case_kind, page=page, page_size=page_size
    )
    return success(data=data)


@router.get("/cases/{case_id}", summary="用例详情")
async def get_case(
    case_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.get_detail(user, case_id)
    return success(data=data)


@router.patch("/cases/{case_id}", summary="编辑用例")
async def update_case(
    case_id: int,
    body: CaseUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.update(user, case_id, body)
    return success(data=data, message="用例更新成功")


@router.delete("/cases/{case_id}", summary="删除用例")
async def delete_case(
    case_id: int,
    user: User = Depends(get_current_active_user),
):
    await CaseService.delete(user, case_id)
    return success(message="用例删除成功")


@router.post("/cases/batch-delete", summary="批量删除用例")
async def batch_delete_cases(
    body: CaseBatchDeleteRequest,
    user: User = Depends(get_current_active_user),
):
    await CaseService.batch_delete(user, body)
    return success(message="批量删除成功")


@router.post("/cases/reuse", summary="复用用例")
async def reuse_cases(
    body: CaseReuseRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.reuse(user, body)
    return success(data=data, message=f"成功复用 {data.created_count} 条用例")


@router.get("/cases/by-interfaces", summary="按接口批量查询用例")
async def list_cases_by_interfaces(
    interface_ids: str = Query(..., description="逗号分隔的接口ID"),
    user: User = Depends(get_current_active_user),
):
    ids = [int(x) for x in interface_ids.split(",") if x.strip().isdigit()]
    data = await CaseService.list_by_interfaces(user, ids)
    return success(data=data)


@router.post("/cases/{case_id}/debug-run", summary="单用例调试")
async def debug_run_case(
    case_id: int,
    body: CaseDebugRunRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.debug_run(user, case_id, environment_id=body.environment_id)
    return success(data=data)


@router.get("/cases/{case_id}/run-records", summary="用例运行历史")
async def list_run_records(
    case_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_active_user),
):
    data = await CaseService.list_run_records(
        user, case_id, page=page, page_size=page_size
    )
    return success(data=data)


@router.get(
    "/interfaces/{interface_id}/cases/generation-status",
    summary="AI预执行进度轮询(v2)",
)
async def get_generation_status(
    interface_id: int,
    session_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    """v2-Q3: 前端每5秒轮询此接口获取预执行进度"""
    data = await ApiCaseGenerationService.get_generation_status(user, interface_id, session_id)
    return success(data=data)
