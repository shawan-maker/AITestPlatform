import logging
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

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
            interface_ids=body.interface_ids,
            api_doc_text=body.api_doc_text,
            user_prompt=body.user_prompt,
            environment_id=body.environment_id,
            title=body.title,
            mode=body.mode,
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

    # ---------- Multi-interface pipeline methods ----------

    @classmethod
    async def stream_pipeline(
        cls,
        user: User,
        session_id: int,
        body: AgentMessageRequest,
    ) -> AsyncIterator[str]:
        """Run the multi-interface pipeline (Phase 1-3) as SSE stream."""
        from service.ai_generation.pipeline import ApiAgentPipeline

        session = await MessageService.ensure_session_access(session_id, user.id)
        if session.gen_type != GenType.api_base:
            raise AppException("非接口用例生成会话", 400)
        await ensure_agent_viewer(session.project_id, user)

        payload = session.output_payload or {}
        mode = payload.get("mode", "from_interfaces")
        interface_ids = payload.get("interface_ids")
        api_doc_text = payload.get("api_doc") or payload.get("api_doc_text")
        user_prompt = body.content or session.user_prompt
        # from_prompt 模式：将用户输入作为接口文档文本
        if mode == "from_prompt" and not api_doc_text:
            import re
            # 剥离前端 buildRichContent 添加的 [context]...[/context] 上下文块
            api_doc_text = re.sub(r'\[context\]\n[\s\S]*?\n\[/context\]\n?', '', user_prompt or "").strip()

        async for chunk in ApiAgentPipeline.run_phase_1_to_3(
            session,
            mode=mode,
            user_prompt=user_prompt,
            interface_ids=interface_ids,
            api_doc_text=api_doc_text,
        ):
            yield chunk

    @classmethod
    async def save_base_cases_and_continue(
        cls,
        user: User,
        session_id: int,
        body,
    ) -> AsyncIterator[str]:
        """Save edited base cases and run Phase 4-5 as SSE stream."""
        from service.ai_generation.pipeline import ApiAgentPipeline
        from service.ai_generation.schemas import SaveBaseCasesRequest

        session = await AIGenerationSession.get_or_none(id=session_id)
        if session is None:
            raise AppException("会话不存在", 404)
        await ensure_agent_editor(session.project_id, user)

        # Update payload with edited base cases
        payload = dict(session.output_payload or {})
        interfaces = payload.get("interfaces", [])

        for edit in body.interfaces:
            if 0 <= edit.index < len(interfaces):
                iface = interfaces[edit.index]
                iface["selected_indexes"] = edit.selected_indexes
                if edit.edited_cases:
                    # Merge edited cases into base_cases by _index
                    for edited in edit.edited_cases:
                        idx = edited.get("_index")
                        if idx is not None and idx < len(iface.get("base_cases", [])):
                            old_expected = iface["base_cases"][idx].get("expected")
                            # Remove _index before merging
                            edit_data = {k: v for k, v in edited.items() if k != "_index"}
                            iface["base_cases"][idx] = {**iface["base_cases"][idx], **edit_data}
                            new_expected = iface["base_cases"][idx].get("expected")
                            logger.info(
                                "[save_base_cases] merge case[%d]: old_expected=%s, new_expected=%s",
                                idx, old_expected, new_expected
                            )

        session.output_payload = payload
        await session.save(update_fields=["output_payload"])

        async for chunk in ApiAgentPipeline.run_phase_4_to_5(
            session,
            environment_id=body.environment_id,
        ):
            yield chunk
