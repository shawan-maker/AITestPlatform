from fastapi import APIRouter, Depends

from service.api_test.debug.schemas import DebugRunRequest, DebugTemplateSaveRequest
from service.api_test.debug.template_service import DebugTemplateService
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(tags=["接口测试-调试"])


@router.get("/interfaces/{interface_id}/debug-template", summary="读取调试模板")
async def get_debug_template(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DebugTemplateService.get_template(user, interface_id)
    return success(data=data)


@router.put("/interfaces/{interface_id}/debug-template", summary="保存调试模板")
async def save_debug_template(
    interface_id: int,
    body: DebugTemplateSaveRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DebugTemplateService.save_template(user, interface_id, body)
    return success(data=data, message="调试模板已保存")


@router.post(
    "/interfaces/{interface_id}/debug-template/fill-from-doc",
    summary="从文档填充调试模板",
)
async def fill_debug_template(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DebugTemplateService.fill_from_doc(user, interface_id)
    return success(data=data, message="模板已填充")


@router.post("/interfaces/{interface_id}/debug-run", summary="接口调试运行")
async def debug_run_interface(
    interface_id: int,
    body: DebugRunRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DebugTemplateService.debug_run(
        user,
        interface_id,
        environment_id=body.environment_id,
        payload=body.payload,
        file_id=body.file_id,
    )
    return success(data=data)
