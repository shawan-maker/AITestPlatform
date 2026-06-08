from collections.abc import AsyncIterator

from service.ai_generation.agent_stream import AgentStreamService, _sse
from service.ai_generation.common import load_knowledge_requirement_text
from service.ai_generation.message_service import MessageService
from service.ai_generation.permissions import ensure_agent_editor, ensure_agent_viewer
from service.ai_generation.schemas import (
    FunctionalCreateSessionRequest,
    FunctionalGenerateRequest,
    FunctionalPreviewUpdateRequest,
    FunctionalSaveRequest,
    GenerationSaveResult,
)
from service.ai_generation.session_lifecycle import SessionLifecycleService, session_to_out
from service.ai_generation.session_schemas import (
    AIGenerationMessageOut,
    AIGenerationSessionListItem,
    AIGenerationSessionOut,
    AgentMessageRequest,
)
from service.core.enums import GenType, SessionStatus, SourceChannel
from service.core.exceptions import AppException
from service.functional_test.case.generation_service import FunctionalCaseGenerationService
from service.functional_test.case.schemas import (
    GenerationPreviewUpdateRequest,
    GenerationSaveRequest,
    GenerationSessionCreateRequest,
)
from service.user.models import User


class FunctionalAgentService:
    @classmethod
    async def create_session(
        cls,
        user: User,
        body: FunctionalCreateSessionRequest,
    ) -> AIGenerationSessionOut:
        await ensure_agent_viewer(body.project_id, user)
        return await SessionLifecycleService.create_functional_session(
            user,
            project_id=body.project_id,
            module_id=body.module_id,
            requirement_text=body.requirement_text,
            knowledge_document_id=body.knowledge_document_id,
            user_prompt=body.user_prompt,
            title=body.title,
        )

    @classmethod
    async def list_sessions(
        cls,
        user: User,
        project_id: int,
    ) -> list[AIGenerationSessionListItem]:
        await ensure_agent_viewer(project_id, user)
        return await SessionLifecycleService.list_agent_sessions(
            user, project_id=project_id, gen_type=GenType.functional
        )

    @classmethod
    async def stream_message(
        cls,
        user: User,
        session_id: int,
        body: AgentMessageRequest,
    ) -> AsyncIterator[str]:
        session = await MessageService.ensure_session_access(session_id, user.id)
        if session.gen_type != GenType.functional:
            raise AppException("非功能用例生成会话", 400)
        await ensure_agent_viewer(session.project_id, user)
        
        # 断点续传：检查session状态，避免重复执行
        refreshed_session = await AIGenerationSession.get(id=session_id)
        
        # 如果session已经有output_payload，说明Agent已成功完成，直接返回结果
        if refreshed_session.output_payload:
            _log.info("[stream_message] session=%s 已有output_payload，直接返回结果", session_id)
            yield _sse("payload_updated", {"session_id": session.id})
            yield _sse("done", {})
            return
        
        # 如果session正在运行（status=running），则返回错误提示
        if refreshed_session.status == SessionStatus.running:
            _log.warning("[stream_message] session=%s 正在执行中，拒绝重复执行", session_id)
            yield _sse("error", {"message": "Agent正在执行中，请等待完成或查看已生成的结果"})
            yield _sse("done", {})
            return
        
        # 否则，正常执行Agent
        async for chunk in AgentStreamService.stream_functional_message(
            session, body.content.strip()
        ):
            yield chunk

    @classmethod
    async def list_messages(
        cls,
        user: User,
        session_id: int,
        *,
        from_sequence: int = 1,
    ) -> list[AIGenerationMessageOut]:
        session = await MessageService.ensure_session_access(session_id, user.id)
        await ensure_agent_viewer(session.project_id, user)
        return await MessageService.list_messages(session, from_sequence=from_sequence)

    @classmethod
    async def generate(
        cls,
        user: User,
        body: FunctionalGenerateRequest,
    ) -> AIGenerationSessionOut:
        """Deprecated: Phase 1 一次性 generate；保留兼容旧客户端。"""
        await ensure_agent_viewer(body.project_id, user)
        if body.knowledge_document_id is not None:
            text = await load_knowledge_requirement_text(
                body.knowledge_document_id, body.project_id
            )
            req = GenerationSessionCreateRequest(
                project_id=body.project_id,
                requirement_text=text,
                knowledge_document_id=body.knowledge_document_id,
                user_prompt=body.user_prompt,
                module_id=body.module_id,
            )
        else:
            req = GenerationSessionCreateRequest(
                project_id=body.project_id,
                requirement_text=body.requirement_text,
                user_prompt=body.user_prompt,
                module_id=body.module_id,
            )
        out = await FunctionalCaseGenerationService.create_session(user, req)
        from service.ai_generation.models import AIGenerationSession

        session = await AIGenerationSession.get(id=out.id)
        session.source_channel = SourceChannel.legacy
        await session.save(update_fields=["source_channel"])
        refreshed = await AIGenerationSession.get(id=out.id)
        return session_to_out(refreshed)

    @classmethod
    async def get_session(
        cls,
        user: User,
        session_id: int,
    ) -> AIGenerationSessionOut:
        session = await FunctionalCaseGenerationService._get_session_or_404(session_id)
        await ensure_agent_viewer(session.project_id, user)
        return session_to_out(session)

    @classmethod
    async def update_preview(
        cls,
        user: User,
        session_id: int,
        body: FunctionalPreviewUpdateRequest,
    ) -> AIGenerationSessionOut:
        out = await FunctionalCaseGenerationService.update_preview(
            user,
            session_id,
            GenerationPreviewUpdateRequest(output_payload=body.output_payload),
        )
        from service.ai_generation.models import AIGenerationSession

        session = await AIGenerationSession.get(id=out.id)
        return session_to_out(session)

    @classmethod
    async def save(
        cls,
        user: User,
        session_id: int,
        body: FunctionalSaveRequest,
    ) -> GenerationSaveResult:
        session = await FunctionalCaseGenerationService._get_session_or_404(session_id)
        await ensure_agent_editor(session.project_id, user)
        return await FunctionalCaseGenerationService.save_cases(
            user,
            session_id,
            GenerationSaveRequest(
                catalog_id=body.catalog_id,
                case_indexes=body.case_indexes,
            ),
        )
