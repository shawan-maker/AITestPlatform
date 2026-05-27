from fastapi import APIRouter, Depends

from service.ai_generation.functional_agent_service import FunctionalAgentService
from service.ai_generation.schemas import (
    FunctionalGenerateRequest,
    FunctionalPreviewUpdateRequest,
    FunctionalSaveRequest,
)
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(prefix="/functional", tags=["AI 智能体-手工用例"])


@router.post("/generate", summary="创建会话并生成手工用例预览")
async def functional_generate(
    body: FunctionalGenerateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.generate(user, body)
    return success(data=data, message="生成会话已创建")


@router.get("/sessions/{session_id}", summary="查询手工用例生成会话")
async def functional_get_session(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.get_session(user, session_id)
    return success(data=data)


@router.patch("/sessions/{session_id}/preview", summary="编辑手工用例生成预览")
async def functional_update_preview(
    session_id: int,
    body: FunctionalPreviewUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.update_preview(user, session_id, body)
    return success(data=data, message="预览已更新")


@router.post("/sessions/{session_id}/save", summary="保存勾选用例到目录")
async def functional_save(
    session_id: int,
    body: FunctionalSaveRequest,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.save(user, session_id, body)
    return success(data=data, message="用例保存成功")
