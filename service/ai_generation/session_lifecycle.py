"""Session create, list, FIFO eviction for agent_center."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

_log = logging.getLogger(__name__)

from service.ai_generation.common import compute_prompt_hash, load_knowledge_document_text
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
        knowledge_document_id: int | None,
        user_prompt: str | None,
        title: str | None,
    ) -> AIGenerationSessionOut:
        await cls._validate_module(project_id, module_id)
        resolved_text = ""
        knowledge_id = None

        if knowledge_document_id is not None:
            resolved_text = await load_knowledge_document_text(
                knowledge_document_id, project_id
            )
            knowledge_id = knowledge_document_id
        else:
            # SIT-F7: Allow empty input (free-form conversation)
            resolved_text = ""

        await cls.enforce_fifo(
            project_id=project_id,
            user_id=user.id,
            gen_type=GenType.functional,
        )
        session = await AIGenerationSession.create(
            project_id=project_id,
            module_id=module_id,
            gen_type=GenType.functional,
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
                content=f"以下为知识库文档全文，供生成用例参考：\n\n{resolved_text}",
                message_type=MessageType.text,
            )
        session.output_payload = session.output_payload or {}
        session.output_payload["_document_context"] = resolved_text
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
        interface_ids: list[int] | None = None,
        api_doc_text: str | None,
        user_prompt: str | None,
        environment_id: int | None = None,
        title: str | None,
        mode: str | None = None,
    ) -> AIGenerationSessionOut:
        await cls._validate_module(project_id, module_id)
        input_ref_type = None
        input_ref_id = None
        source_text = ""

        # Determine mode
        if mode is None:
            if interface_ids and len(interface_ids) > 1:
                mode = "from_interfaces"
            elif interface_id:
                mode = "single"
            elif api_doc_text and api_doc_text.strip():
                mode = "from_doc"
            elif interface_ids and len(interface_ids) == 1:
                mode = "single"
                interface_id = interface_ids[0]

        if mode == "from_interfaces" and interface_ids:
            # Multi-interface mode
            input_ref_type = InputRefType.multi_iface
            source_text = user_prompt or f"接口用例生成({len(interface_ids)}个接口)"

        elif interface_id is not None:
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
            # Allow empty input for pipeline mode (user just selects interfaces)
            source_text = user_prompt or ""
            input_ref_type = InputRefType.multi_iface

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

        extra: dict = {"mode": mode or "single"}
        if mode == "from_interfaces" and interface_ids:
            extra["interface_ids"] = interface_ids
        elif mode == "from_doc" and api_doc_text:
            extra["api_doc"] = api_doc_text
        elif mode == "from_prompt" and user_prompt:
            extra["api_doc"] = user_prompt  # from_prompt 模式：user_prompt 即原始接口文档
        elif interface_id:
            extra["api_doc"] = source_text
            from service.api_test.dependency.resolver_service import DependencyResolverService
            resolved = await DependencyResolverService.resolve(interface_id)
            extra["precoditions_api_doc"] = resolved.precoditions_api_doc
            extra["precoditions"] = resolved.precoditions_summaries

        if environment_id:
            extra["environment_id"] = environment_id

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
    def _default_title(text: str | None = None, max_len: int = 30) -> str:
        """Generate initial temp title. Final title will be replaced by LLM after SSE done."""
        if not text or not text.strip():
            return "新对话"
        one_line = " ".join(text.split())
        if len(one_line) <= max_len:
            return one_line
        # Ensure truncated result ends with '...' and total length <= max_len
        return one_line[: max_len - 3].rstrip() + "..."

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

    @classmethod
    async def cleanup_stale_sessions(cls) -> int:
        """清理启动时仍为 running 状态的孤儿会话（服务重启残留）。"""
        stale_sessions = await AIGenerationSession.filter(status=SessionStatus.running)
        count = 0
        for session in stale_sessions:
            session.status = SessionStatus.failed
            session.error_message = "服务重启，任务中断"
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["status", "error_message", "finished_at"])
            count += 1
        if count:
            _log.info("[cleanup] 清理了 %d 个 stale running sessions", count)
        return count

    # ---------- SIT-F7: Session management (rename / delete) ----------

    @classmethod
    async def rename_session(
        cls,
        user: User,
        *,
        session_id: int,
        new_title: str,
    ) -> AIGenerationSessionOut:
        """Rename a session title (editor+ on own sessions or project admin)."""
        session = await AIGenerationSession.get_or_none(id=session_id)
        if not session:
            raise AppException("会话不存在", 404)
        if session.project_id:
            # TODO: add project-level editor permission check here
            pass
        if not new_title or not new_title.strip():
            raise AppException("标题不能为空", 400)
        session.title = new_title.strip()
        await session.save(update_fields=["title"])
        return session_to_out(session)

    @classmethod
    async def delete_session(
        cls,
        user: User,
        *,
        session_id: int,
    ) -> dict:
        """Delete a session and cascade messages (editor+). Running sessions rejected with 409."""
        session = await AIGenerationSession.get_or_none(id=session_id)
        if not session:
            raise AppException("会话不存在", 404)
        if session.status == SessionStatus.running:
            raise AppException("对话正在进行中，请先结束对话后再删除", 409)
        sid = session.id
        await AIGenerationMessage.filter(session_id=sid).delete()
        await AIGenerationSession.filter(id=sid).delete()
        return {"success": True}

    @classmethod
    async def summarize_and_update_title(cls, user: User, *, session_id: int) -> AIGenerationSessionOut:
        """Generate AI title and update session."""
        import os
        log_file = "d:/PyProject/AITestPlatform/debug_title.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[DEBUG] summarize_and_update_title called, session_id: {session_id}\n")
        
        session = await AIGenerationSession.get_or_none(id=session_id)
        if not session:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[DEBUG] Session not found: {session_id}\n")
            raise AppException("会话不存在", 404)
        
        first_msg = await AIGenerationMessage.filter(
            session_id=session_id, role="user"
        ).order_by("sequence").first()
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[DEBUG] first_msg: {first_msg}\n")
        
        if first_msg and first_msg.content:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[DEBUG] first_msg.content: {first_msg.content[:100]}...\n")
            
            new_title = await cls.summarize_session_title(
                session_id=session_id, user_first_msg=first_msg.content[:500]
            )
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[DEBUG] new_title: {new_title}\n")
            
            if new_title:
                session.title = new_title[:200]
                await session.save(update_fields=["title"])
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[DEBUG] session.title updated to: {session.title}\n")
        else:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[DEBUG] No user message found, cannot generate title\n")
        
        return session_to_out(session)

    @classmethod
    async def summarize_session_title(cls, *, session_id: int, user_first_msg: str) -> str | None:
        """Call LLM to generate a semantic summary title for the session.
        Returns the new title string, or None on failure (silently degrade).
        """
        import json

        from service.ai_generation.common import SESSION_TITLE_PROMPT, is_llm_configured
        from service.core import config as core_config

        if not is_llm_configured():
            return None
        try:
            import httpx

            api_key = os.getenv("LLM_BINDING_API_KEY")
            # 修复：使用LLM_BINDING_HOST而不是LLM_BASE_URL
            base_url = os.getenv("LLM_BINDING_HOST", "https://api.openai.com/v1")
            model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
            
            _log.info("[summarize_session_title] api_key存在: %s, base_url: %s, model: %s", 
                     bool(api_key), base_url, model)

            prompt = SESSION_TITLE_PROMPT.format(user_first_message=user_first_msg[:500])
            _log.info("[summarize_session_title] 正在调用LLM生成标题, prompt长度: %d", len(prompt))
            
            resp = httpx.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 20,
                    "temperature": 0.3,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            _log.info("[summarize_session_title] LLM响应: %s", str(data)[:200])
            
            title = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            _log.info("[summarize_session_title] 生成的标题: %s", title)
            return title if title else None
        except Exception as e:
            _log.error("[summarize_session_title] 生成标题失败: %s", e, exc_info=True)
            return None
