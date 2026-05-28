"""Session create, list, FIFO eviction for agent_center."""

from __future__ import annotations

from datetime import datetime, timezone

from service.ai_generation.common import compute_prompt_hash, load_knowledge_requirement_text
from service.ai_generation.message_service import MessageService
from service.ai_generation.models import AIGenerationMessage, AIGenerationSession
from service.ai_generation.session_schemas import AIGenerationSessionListItem, AIGenerationSessionOut
from service.core import config as core_config
from service.core.enums import GenType, InputRefType, MessageRole, MessageType, SessionStatus, SourceChannel
from service.core.exceptions import AppException
from service.project.models import Project, ProjectModule
from service.user.models import User


def session_to_out(session: AIGenerationSession) -> AIGenerationSessionOut:
    return AIGenerationSessionOut(
        id=session.id,
        project_id=session.project_id,
        module_id=session.module_id,
        gen_type=session.gen_type,
        status=session.status,
        error_message=session.error_message,
        output_payload=session.output_payload,
        user_prompt=session.user_prompt,
        source_channel=session.source_channel,
        title=session.title,
        created_at=session.created_at,
        finished_at=session.finished_at,
    )


def session_to_list_item(session: AIGenerationSession) -> AIGenerationSessionListItem:
    return AIGenerationSessionListItem(
        id=session.id,
        project_id=session.project_id,
        gen_type=session.gen_type,
        status=session.status,
        title=session.title,
        created_at=session.created_at,
        finished_at=session.finished_at,
    )


class SessionLifecycleService:
    @classmethod
    async def enforce_fifo(
        cls,
        *,
        project_id: int,
        user_id: int,
        gen_type: GenType,
        source_channel: SourceChannel = SourceChannel.agent_center,
    ) -> None:
        import os

        from service.core import config as core_config

        limit = int(os.getenv("AI_AGENT_SESSION_HISTORY_LIMIT", str(core_config.AI_AGENT_SESSION_HISTORY_LIMIT)))
        if limit <= 0:
            return
        qs = AIGenerationSession.filter(
            project_id=project_id,
            created_by_id=user_id,
            gen_type=gen_type,
            source_channel=source_channel,
        ).order_by("created_at")
        count = await qs.count()
        if count < limit:
            return
        to_remove = count - limit + 1
        oldest = await qs.limit(to_remove)
        ids = [s.id for s in oldest]
        await AIGenerationMessage.filter(session_id__in=ids).delete()
        await AIGenerationSession.filter(id__in=ids).delete()

    @classmethod
    async def create_functional_session(
        cls,
        user: User,
        *,
        project_id: int,
        module_id: int | None,
        requirement_text: str | None,
        knowledge_document_id: int | None,
        user_prompt: str | None,
        title: str | None,
    ) -> AIGenerationSessionOut:
        await cls._validate_module(project_id, module_id)
        resolved_text = ""
        input_ref_type = None
        input_ref_id = None
        knowledge_id = None

        if knowledge_document_id is not None:
            if requirement_text and requirement_text.strip():
                raise AppException("requirement_text 与 knowledge_document_id 不能同时提供", 400)
            resolved_text = await load_knowledge_requirement_text(
                knowledge_document_id, project_id
            )
            knowledge_id = knowledge_document_id
        elif requirement_text and requirement_text.strip():
            resolved_text = requirement_text.strip()
        else:
            raise AppException("requirement_text 或 knowledge_document_id 至少提供一个", 400)

        await cls.enforce_fifo(
            project_id=project_id,
            user_id=user.id,
            gen_type=GenType.functional,
        )
        session = await AIGenerationSession.create(
            project_id=project_id,
            module_id=module_id,
            gen_type=GenType.functional,
            input_ref_type=input_ref_type,
            input_ref_id=input_ref_id,
            knowledge_document_id=knowledge_id,
            prompt_hash=compute_prompt_hash(resolved_text, user_prompt),
            status=SessionStatus.pending,
            user_prompt=user_prompt,
            source_channel=SourceChannel.agent_center,
            title=title or cls._default_title(resolved_text),
            created_by_id=user.id,
        )
        if knowledge_id:
            await MessageService.append(
                session.id,
                role=MessageRole.system,
                content=f"以下为知识库需求文档全文，供生成用例参考：\n\n{resolved_text}",
                message_type=MessageType.text,
            )
        session.output_payload = session.output_payload or {}
        session.output_payload["_requirement_context"] = resolved_text
        await session.save(update_fields=["output_payload"])
        return session_to_out(session)

    @classmethod
    async def create_api_session(
        cls,
        user: User,
        *,
        project_id: int,
        module_id: int | None,
        interface_id: int | None,
        api_doc_text: str | None,
        user_prompt: str | None,
        title: str | None,
    ) -> AIGenerationSessionOut:
        await cls._validate_module(project_id, module_id)
        input_ref_type = None
        input_ref_id = None
        source_text = ""

        if interface_id is not None:
            from service.api_test.interface.interface_service import InterfaceService
            from service.api_test.shared.interface_doc import interface_to_doc_json

            iface = await InterfaceService._get_current_or_404(interface_id)
            if iface.project_id != project_id:
                raise AppException("接口不属于该项目", 400)
            input_ref_type = InputRefType.interface
            input_ref_id = iface.id
            source_text = interface_to_doc_json(iface)
            module_id = module_id or iface.module_id
        elif api_doc_text and api_doc_text.strip():
            source_text = api_doc_text.strip()
            input_ref_type = InputRefType.api_doc
        else:
            raise AppException("interface_id 或 api_doc_text 至少提供一个", 400)

        await cls.enforce_fifo(
            project_id=project_id,
            user_id=user.id,
            gen_type=GenType.api_base,
        )
        session = await AIGenerationSession.create(
            project_id=project_id,
            module_id=module_id,
            gen_type=GenType.api_base,
            input_ref_type=input_ref_type,
            input_ref_id=input_ref_id,
            prompt_hash=compute_prompt_hash(source_text, user_prompt),
            status=SessionStatus.pending,
            user_prompt=user_prompt,
            source_channel=SourceChannel.agent_center,
            title=title or cls._default_title(source_text),
            created_by_id=user.id,
        )
        extra: dict = {"api_doc": source_text}
        if interface_id:
            from service.api_test.dependency.resolver_service import DependencyResolverService

            resolved = await DependencyResolverService.resolve(interface_id)
            extra["precoditions_api_doc"] = resolved.precoditions_api_doc
            extra["precoditions"] = resolved.precoditions_summaries
        session.output_payload = extra
        await session.save(update_fields=["output_payload"])
        return session_to_out(session)

    @classmethod
    async def list_agent_sessions(
        cls,
        user: User,
        *,
        project_id: int,
        gen_type: GenType,
    ) -> list[AIGenerationSessionListItem]:
        rows = await AIGenerationSession.filter(
            project_id=project_id,
            created_by_id=user.id,
            gen_type=gen_type,
            source_channel=SourceChannel.agent_center,
        ).order_by("-created_at")
        return [session_to_list_item(s) for s in rows]

    @classmethod
    async def get_project_name(cls, project_id: int) -> str:
        project = await Project.get_or_none(id=project_id)
        return project.name if project else str(project_id)

    @staticmethod
    def _default_title(text: str, max_len: int = 50) -> str:
        one_line = " ".join(text.split())
        if len(one_line) <= max_len:
            return one_line
        return one_line[: max_len - 3] + "..."

    @staticmethod
    async def _validate_module(project_id: int, module_id: int | None) -> None:
        if module_id is None:
            return
        exists = await ProjectModule.filter(id=module_id, project_id=project_id).exists()
        if not exists:
            raise AppException("项目模块不存在", 404)

    @classmethod
    async def mark_running(cls, session: AIGenerationSession) -> None:
        session.status = SessionStatus.running
        session.error_message = None
        await session.save(update_fields=["status", "error_message"])

    @classmethod
    async def mark_failed(cls, session: AIGenerationSession, message: str) -> None:
        session.status = SessionStatus.failed
        session.error_message = message
        session.finished_at = datetime.now(timezone.utc)
        await session.save(update_fields=["status", "error_message", "finished_at"])
