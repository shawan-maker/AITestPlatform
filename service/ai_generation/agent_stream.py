"""Stream Agent turns as SSE events and persist messages."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from service.ai_generation.common import (
    api_test_gen_use_mock,
    functional_gen_use_mock,
    is_llm_configured,
    LLM_NOT_CONFIGURED_MSG,
)
from service.ai_generation.message_service import MessageService
from service.ai_generation.models import AIGenerationSession
from service.ai_generation.payload_sync import sync_api_base_payload, sync_functional_payload
from service.ai_generation.session_lifecycle import SessionLifecycleService
from service.core.enums import GenType, MessageRole, MessageType, SessionStatus
from service.functional_test.case.generation_service import FunctionalCaseGenerationService


def _sse(event: str, data: Any) -> str:
    if isinstance(data, str):
        payload = json.dumps(data, ensure_ascii=False)
    elif isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = json.dumps(str(data), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


class AgentStreamService:
    @classmethod
    async def stream_functional_message(
        cls,
        session: AIGenerationSession,
        user_content: str,
    ) -> AsyncIterator[str]:
        async for chunk in cls._stream_turn(session, user_content, gen_type=GenType.functional):
            yield chunk

    @classmethod
    async def stream_api_message(
        cls,
        session: AIGenerationSession,
        user_content: str,
    ) -> AsyncIterator[str]:
        async for chunk in cls._stream_turn(session, user_content, gen_type=GenType.api_base):
            yield chunk

    @classmethod
    async def _stream_turn(
        cls,
        session: AIGenerationSession,
        user_content: str,
        *,
        gen_type: GenType,
    ) -> AsyncIterator[str]:
        await MessageService.append(
            session.id,
            role=MessageRole.user,
            content=user_content,
            message_type=MessageType.text,
        )
        await SessionLifecycleService.mark_running(session)

        try:
            if gen_type == GenType.functional and functional_gen_use_mock():
                async for evt in cls._mock_functional(session, user_content):
                    yield evt
            elif gen_type == GenType.api_base and api_test_gen_use_mock():
                async for evt in cls._mock_api(session, user_content):
                    yield evt
            elif not is_llm_configured():
                await SessionLifecycleService.mark_failed(session, LLM_NOT_CONFIGURED_MSG)
                yield _sse("error", {"message": LLM_NOT_CONFIGURED_MSG})
            else:
                async for evt in cls._stream_agent(session, user_content, gen_type=gen_type):
                    yield evt
            yield _sse("payload_updated", {"session_id": session.id})
            yield _sse("done", {})
        except Exception as exc:
            msg = str(exc) or repr(exc)
            await SessionLifecycleService.mark_failed(session, msg)
            yield _sse("error", {"message": msg})

    @classmethod
    async def _mock_functional(
        cls,
        session: AIGenerationSession,
        user_content: str,
    ) -> AsyncIterator[str]:
        ctx = (session.output_payload or {}).get("_requirement_context") or user_content
        payload = FunctionalCaseGenerationService._mock_payload(ctx)
        await sync_functional_payload(
            session.id,
            {"points": payload["test_points"], "test_cases": payload["cases"]},
        )
        text = "已生成功能用例预览（mock）。"
        await MessageService.append(
            session.id,
            role=MessageRole.assistant,
            content=text,
            message_type=MessageType.text,
        )
        yield _sse("messages", text)

    @classmethod
    async def _mock_api(
        cls,
        session: AIGenerationSession,
        user_content: str,
    ) -> AsyncIterator[str]:
        from service.api_test.case.generation_service import ApiCaseGenerationService

        label = user_content[:40] or "mock-api"
        base_cases = ApiCaseGenerationService._mock_base_cases(label)
        extra = dict(session.output_payload or {})
        await sync_api_base_payload(
            session.id,
            base_cases=base_cases,
            api_doc=extra.get("api_doc"),
            extra={k: v for k, v in extra.items() if k != "base_cases"},
        )
        text = "已生成接口基础用例预览（mock）。"
        await MessageService.append(
            session.id,
            role=MessageRole.assistant,
            content=text,
            message_type=MessageType.text,
        )
        yield _sse("messages", text)

    @classmethod
    async def _stream_agent(
        cls,
        session: AIGenerationSession,
        user_content: str,
        *,
        gen_type: GenType,
    ) -> AsyncIterator[str]:
        from agents.case_generate_agent import AgentManage
        from agents.memory.manager import RuntimeContext

        project_name = await SessionLifecycleService.get_project_name(session.project_id)
        thread_prefix = "functional" if gen_type == GenType.functional else "api"
        context = RuntimeContext(
            project_name=project_name,
            module_id=str(session.module_id or ""),
            user_id=str(session.created_by_id),
            session_id=str(session.id),
            thread_id=f"{thread_prefix}-{session.id}",
        )
        if gen_type == GenType.functional:
            agent = AgentManage.create_case_generate_agent()
        else:
            agent = AgentManage.create_api_case_generate_agent()

        run_config = {
            "configurable": {
                "thread_id": context.thread_id,
                "ai_session_id": session.id,
            }
        }

        assistant_buffer: list[str] = []

        def _run_stream():
            return list(
                AgentManage.agent_chat(
                    agent,
                    user_content,
                    context,
                    run_config=run_config,
                )
            )

        items = await asyncio.to_thread(_run_stream)
        for item in items:
            kind = item.get("type")
            content = item.get("content", "")
            if kind == "custom":
                await MessageService.append(
                    session.id,
                    role=MessageRole.tool,
                    content=str(content),
                    message_type=MessageType.custom,
                )
                yield _sse("custom", str(content))
            elif kind == "messages":
                assistant_buffer.append(str(content))
                yield _sse("messages", str(content))
            elif kind == "tool_call":
                tool_name = item.get("tool_name")
                await MessageService.append(
                    session.id,
                    role=MessageRole.tool,
                    content=str(content),
                    message_type=MessageType.tool_call,
                    tool_name=tool_name,
                )
                yield _sse("tool_call", {"name": tool_name, "content": content})

        if assistant_buffer:
            await MessageService.append(
                session.id,
                role=MessageRole.assistant,
                content="".join(assistant_buffer),
                message_type=MessageType.text,
            )

        refreshed = await AIGenerationSession.get(id=session.id)
        if refreshed.status != SessionStatus.success and refreshed.output_payload:
            refreshed.status = SessionStatus.success
            refreshed.finished_at = datetime.now(timezone.utc)
            await refreshed.save(update_fields=["status", "finished_at"])
