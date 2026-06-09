from collections.abc import AsyncIterator
import logging

from service.ai_generation.agent_stream import AgentStreamService, _sse

_log = logging.getLogger(__name__)
from service.ai_generation.common import load_knowledge_document_text
from service.ai_generation.message_service import MessageService
from service.ai_generation.models import AIGenerationSession
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
        _log.info("[stream_message] 🚀 开始执行 session=%s", session_id)
        _log.info("[stream_message] 请求内容: %s", body.content[:100] if body.content else 'EMPTY')
        
        session = await MessageService.ensure_session_access(session_id, user.id)
        if session.gen_type != GenType.functional:
            _log.error("[stream_message] ❌ 非功能用例生成会话 session=%s", session_id)
            raise AppException("非功能用例生成会话", 400)
        
        await ensure_agent_viewer(session.project_id, user)
        _log.info("[stream_message] ✅ 权限检查通过 session=%s", session_id)
        
        # 正常执行Agent（移除断点续传检查，避免状态判断错误）
        _log.info("[stream_message] 🔄 开始流式返回 session=%s", session_id)
        chunk_count = 0
        async for chunk in AgentStreamService.stream_functional_message(
            session, body.content.strip()
        ):
            chunk_count += 1
            if chunk_count % 10 == 0:  # 每10个chunk记录一次
                _log.info("[stream_message] 已发送 %s 个chunk session=%s", chunk_count, session_id)
            yield chunk
        
        _log.info("[stream_message] ✅ 流式返回完成，共 %s 个chunk session=%s", chunk_count, session_id)

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
        """Deprecated: Phase1 一次性 generate；保留兼容旧客户端。"""
        await ensure_agent_viewer(body.project_id, user)
        req = GenerationSessionCreateRequest(
            project_id=body.project_id,
            knowledge_document_id=body.knowledge_document_id,
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
