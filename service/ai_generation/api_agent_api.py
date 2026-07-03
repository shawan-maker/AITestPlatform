from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from service.ai_generation.api_agent_service import ApiAgentService
from service.ai_generation.schemas import (
    ApiConfirmRequest,
    ApiCreateSessionRequest,
    ApiGenerateFromDocRequest,
    ApiGenerateFromInterfaceRequest,
    ApiSessionPreviewUpdateRequest,
    SaveBaseCasesRequest,
)
from service.ai_generation.session_schemas import AgentMessageRequest, SessionRenameRequest
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(prefix="/api", tags=["AI 智能体-接口用例"])


@router.post("/sessions", summary="创建接口用例 Agent 会话")
async def api_create_session(
    body: ApiCreateSessionRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.create_session(user, body)
    return success(data=data, message="会话已创建")


@router.get("/sessions", summary="接口用例 Agent 历史会话列表")
async def api_list_sessions(
    project_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.list_sessions(user, project_id)
    return success(data=data)


@router.get("/sessions/{session_id}", summary="查询接口用例生成会话")
async def api_get_session(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.get_session(user, session_id)
    return success(data=data)


@router.post("/sessions/{session_id}/messages", summary="发送消息（SSE 流式）")
async def api_post_message(
    session_id: int,
    body: AgentMessageRequest,
    user: User = Depends(get_current_active_user),
):
    # Detect pipeline mode: if session has mode != "single", use pipeline
    from service.ai_generation.models import AIGenerationSession
    session = await AIGenerationSession.get_or_none(id=session_id)
    if session and session.output_payload:
        mode = session.output_payload.get("mode")
        if mode in ("from_interfaces", "from_doc", "from_prompt"):
            stream = ApiAgentService.stream_pipeline(user, session_id, body)
            return StreamingResponse(stream, media_type="text/event-stream")
    # Fallback to legacy agent flow
    stream = ApiAgentService.stream_message(user, session_id, body)
    return StreamingResponse(stream, media_type="text/event-stream")


@router.get("/sessions/{session_id}/messages", summary="回放会话消息")
async def api_list_messages(
    session_id: int,
    from_sequence: int = Query(1, ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.list_messages(
        user, session_id, from_sequence=from_sequence
    )
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


@router.post(
    "/generate-from-interface",
    summary="[deprecated] 从已有接口生成用例预览",
    deprecated=True,
)
async def api_generate_from_interface(
    body: ApiGenerateFromInterfaceRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.generate_from_interface(user, body)
    return success(data=data)


@router.post(
    "/generate-from-doc",
    summary="[deprecated] 从接口文档生成用例预览",
    deprecated=True,
)
async def api_generate_from_doc(
    body: ApiGenerateFromDocRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ApiAgentService.generate_from_doc(user, body)
    return success(data=data)


# ---------- SIT-F7: Session management (rename / delete) ----------

@router.patch("/sessions/{session_id}", summary="重命名接口用例 Agent 会话")
async def api_rename_session(
    session_id: int,
    body: SessionRenameRequest,
    user: User = Depends(get_current_active_user),
):
    from service.ai_generation.session_lifecycle import SessionLifecycleService
    data = await SessionLifecycleService.rename_session(user, session_id=session_id, new_title=body.title)
    return success(data=data, message="会话名称已更新")


@router.delete("/sessions/{session_id}", summary="删除接口用例 Agent 会话")
async def api_delete_session(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    from service.ai_generation.session_lifecycle import SessionLifecycleService
    data = await SessionLifecycleService.delete_session(user, session_id=session_id)
    return success(data=data, message="会话已删除")


@router.post("/sessions/{session_id}/summarize-title", summary="AI 生成会话标题")
async def api_summarize_title(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    from service.ai_generation.session_lifecycle import SessionLifecycleService
    data = await SessionLifecycleService.summarize_and_update_title(user, session_id=session_id)
    return success(data=data, message="标题已更新")


# ---------- Multi-interface pipeline endpoints ----------

@router.post(
    "/sessions/{session_id}/save-base-cases",
    summary="保存编辑后的基础用例并触发结构化+预执行",
)
async def api_save_base_cases(
    session_id: int,
    body: SaveBaseCasesRequest,
    user: User = Depends(get_current_active_user),
):
    stream = ApiAgentService.save_base_cases_and_continue(user, session_id, body)
    return StreamingResponse(stream, media_type="text/event-stream")
