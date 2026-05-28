from collections.abc import AsyncIterator

from service.ai_generation.agent_stream import AgentStreamService
from service.ai_generation.message_service import MessageService
from service.ai_generation.models import AIGenerationSession
from service.ai_generation.permissions import ensure_agent_editor, ensure_agent_viewer
from service.ai_generation.schemas import (
    ApiConfirmRequest,
    ApiConfirmResult,
    ApiCreateSessionRequest,
    ApiGenerateFromDocRequest,
    ApiGenerateFromInterfaceRequest,
    ApiSessionPreviewUpdateRequest,
    GeneratePreviewResult,
)
from service.ai_generation.session_lifecycle import SessionLifecycleService, session_to_out
from service.ai_generation.session_schemas import (
    AIGenerationMessageOut,
    AIGenerationSessionListItem,
    AIGenerationSessionOut,
    AgentMessageRequest,
)
from service.api_test.case.generation_service import ApiCaseGenerationService
from service.api_test.case.schemas import (
    GeneratePreviewRequest,
    PreviewFromDocRequest,
)
from service.api_test.interface.interface_service import InterfaceService
from service.core.enums import GenType, SourceChannel
from service.core.exceptions import AppException
from service.user.models import User


class ApiAgentService:
    @classmethod
    async def create_session(
        cls,
        user: User,
        body: ApiCreateSessionRequest,
    ) -> AIGenerationSessionOut:
        await ensure_agent_viewer(body.project_id, user)
        return await SessionLifecycleService.create_api_session(
            user,
            project_id=body.project_id,
            module_id=body.module_id,
            interface_id=body.interface_id,
            api_doc_text=body.api_doc_text,
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
            user, project_id=project_id, gen_type=GenType.api_base
        )

    @classmethod
    async def stream_message(
        cls,
        user: User,
        session_id: int,
        body: AgentMessageRequest,
    ) -> AsyncIterator[str]:
        session = await MessageService.ensure_session_access(session_id, user.id)
        if session.gen_type != GenType.api_base:
            raise AppException("非接口用例生成会话", 400)
        await ensure_agent_viewer(session.project_id, user)
        async for chunk in AgentStreamService.stream_api_message(session, body.content.strip()):
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
    async def generate_from_interface(
        cls,
        user: User,
        body: ApiGenerateFromInterfaceRequest,
    ) -> GeneratePreviewResult:
        iface = await InterfaceService._get_current_or_404(body.interface_id)
        await ensure_agent_viewer(iface.project_id, user)
        result = await ApiCaseGenerationService.preview(
            user,
            body.interface_id,
            GeneratePreviewRequest(
                environment_id=body.environment_id,
                user_prompt=body.user_prompt,
            ),
        )
        session = await AIGenerationSession.get(id=result.session_id)
        session.source_channel = SourceChannel.legacy
        await session.save(update_fields=["source_channel"])
        return result

    @classmethod
    async def generate_from_doc(
        cls,
        user: User,
        body: ApiGenerateFromDocRequest,
    ) -> GeneratePreviewResult:
        await ensure_agent_viewer(body.project_id, user)
        result = await ApiCaseGenerationService.preview_from_doc(
            user,
            PreviewFromDocRequest(
                project_id=body.project_id,
                api_doc_text=body.api_doc_text,
                user_prompt=body.user_prompt,
                module_id=body.module_id,
            ),
        )
        session = await AIGenerationSession.get(id=result.session_id)
        session.source_channel = SourceChannel.legacy
        await session.save(update_fields=["source_channel"])
        return result

    @classmethod
    async def get_session(
        cls,
        user: User,
        session_id: int,
    ) -> AIGenerationSessionOut:
        out = await ApiCaseGenerationService.get_session(user, session_id)
        session = await AIGenerationSession.get(id=out.id)
        return session_to_out(session)

    @classmethod
    async def update_preview(
        cls,
        user: User,
        session_id: int,
        body: ApiSessionPreviewUpdateRequest,
    ) -> AIGenerationSessionOut:
        out = await ApiCaseGenerationService.update_preview(user, session_id, body)
        session = await AIGenerationSession.get(id=out.id)
        return session_to_out(session)

    @classmethod
    async def confirm(
        cls,
        user: User,
        body: ApiConfirmRequest,
    ) -> ApiConfirmResult:
        session = await AIGenerationSession.get_or_none(id=body.session_id)
        if session is None:
            raise AppException("生成会话不存在", 404)
        await ensure_agent_editor(session.project_id, user)
        return await ApiCaseGenerationService.confirm_session(user, body)
