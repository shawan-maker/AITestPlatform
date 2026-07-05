from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from service.ai_generation.functional_agent_service import FunctionalAgentService
from service.ai_generation.schemas import (
    FunctionalCreateSessionRequest,
    FunctionalGenerateRequest,
    FunctionalPreviewUpdateRequest,
    FunctionalSaveRequest,
)
from service.ai_generation.session_schemas import AgentMessageRequest, SessionRenameRequest
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(prefix="/functional", tags=["AI 智能体-手工用例"])


@router.post("/sessions", summary="创建手工用例 Agent 会话")
async def functional_create_session(
    body: FunctionalCreateSessionRequest,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.create_session(user, body)
    return success(data=data, message="会话已创建")


@router.get("/sessions", summary="手工用例 Agent 历史会话列表")
async def functional_list_sessions(
    project_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.list_sessions(user, project_id)
    return success(data=data)


@router.get("/sessions/{session_id}", summary="查询手工用例生成会话")
async def functional_get_session(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.get_session(user, session_id)
    return success(data=data)


@router.post("/sessions/{session_id}/messages", summary="发送消息（SSE 流式）")
async def functional_post_message(
    session_id: int,
    body: AgentMessageRequest,
    user: User = Depends(get_current_active_user),
):
    stream = FunctionalAgentService.stream_message(user, session_id, body)
    return StreamingResponse(stream, media_type="text/event-stream")


@router.post("/sessions/{session_id}/reconnect", summary="SSE 断线重连（重放缓冲事件 + 接入实时流）")
async def functional_reconnect_session(
    session_id: int,
    last_seq: int = Query(-1, ge=-1, description="客户端收到的最后一个事件序号"),
    user: User = Depends(get_current_active_user),
):
    """SSE reconnect endpoint for functional agent sessions."""
    from service.ai_generation.models import AIGenerationSession
    from service.ai_generation.agent_stream import AgentStreamService

    session = await AIGenerationSession.get_or_none(id=session_id)
    if not session:
        return success(data=None, message="会话不存在")

    stream = AgentStreamService.stream_reconnect(session, last_seq=last_seq)
    return StreamingResponse(stream, media_type="text/event-stream")


@router.get("/sessions/{session_id}/messages", summary="回放会话消息")
async def functional_list_messages(
    session_id: int,
    from_sequence: int = Query(1, ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.list_messages(
        user, session_id, from_sequence=from_sequence
    )
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


@router.post(
    "/generate",
    summary="[deprecated] 创建会话并异步生成手工用例预览",
    deprecated=True,
)
async def functional_generate(
    body: FunctionalGenerateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalAgentService.generate(user, body)
    return success(data=data, message="生成会话已创建")


# ---------- SIT-F7: Session management (rename / delete) ----------

@router.patch("/sessions/{session_id}", summary="重命名手工用例 Agent 会话")
async def functional_rename_session(
    session_id: int,
    body: SessionRenameRequest,
    user: User = Depends(get_current_active_user),
):
    from service.ai_generation.session_lifecycle import SessionLifecycleService
    data = await SessionLifecycleService.rename_session(user, session_id=session_id, new_title=body.title)
    return success(data=data, message="会话名称已更新")


@router.post("/sessions/{session_id}/summarize-title", summary="AI 生成会话标题")
async def functional_summarize_title(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    from service.ai_generation.session_lifecycle import SessionLifecycleService
    data = await SessionLifecycleService.summarize_and_update_title(user, session_id=session_id)
    return success(data=data, message="标题已更新")


@router.delete("/sessions/{session_id}", summary="删除手工用例 Agent 会话")
async def functional_delete_session(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    from service.ai_generation.session_lifecycle import SessionLifecycleService
    data = await SessionLifecycleService.delete_session(user, session_id=session_id)
    return success(data=data, message="会话已删除")
