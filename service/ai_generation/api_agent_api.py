from fastapi import APIRouter, Depends

from service.ai_generation.api_agent_service import ApiAgentService
from service.ai_generation.schemas import (
    ApiConfirmRequest,
    ApiGenerateFromDocRequest,
    ApiGenerateFromInterfaceRequest,
    ApiSessionPreviewUpdateRequest,
)
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(prefix="/api", tags=["AI 智能体-接口用例"])


@router.post("/generate-from-interface", summary="从已有接口生成用例预览")
async def api_generate_from_interface(
    body: ApiGenerateFromInterfaceRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.generate_from_interface(user, body)
    return success(data=data)


@router.post("/generate-from-doc", summary="从接口文档生成用例预览")
async def api_generate_from_doc(
    body: ApiGenerateFromDocRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.generate_from_doc(user, body)
    return success(data=data)


@router.get("/sessions/{session_id}", summary="查询接口用例生成会话")
async def api_get_session(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.get_session(user, session_id)
    return success(data=data)


@router.patch("/sessions/{session_id}/preview", summary="编辑接口用例生成预览")
async def api_update_preview(
    session_id: int,
    body: ApiSessionPreviewUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.update_preview(user, session_id, body)
    return success(data=data, message="预览已更新")


@router.post("/confirm", summary="确认生成并入库")
async def api_confirm(
    body: ApiConfirmRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.confirm(user, body)
    return success(data=data, message="用例生成完成")
