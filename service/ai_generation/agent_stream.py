"""Stream Agent turns as SSE events and persist messages."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
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

# Agent execution timeout in seconds (default 10 min), configurable via env
_AGENT_TIMEOUT_SECONDS = int(os.getenv("AI_AGENT_TIMEOUT_SECONDS", "600"))

_log = logging.getLogger("agent_stream")


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
        _log.info("[SSE] 🚀 _stream_turn 开始 session=%s, gen_type=%s", session.id, gen_type)
        _log.info("[SSE] 用户内容: %s", user_content[:100] if user_content else 'EMPTY')
        
        await MessageService.append(
            session.id,
            role=MessageRole.user,
            content=user_content,
            message_type=MessageType.text,
        )
        _log.info("[SSE] 用户消息已保存 session=%s", session.id)
        
        await SessionLifecycleService.mark_running(session)
        _log.info("[SSE] Session 状态已标记为 running session=%s", session.id)

        try:
            if gen_type == GenType.functional and functional_gen_use_mock():
                _log.info("[SSE] 使用 Mock 模式 (functional) session=%s", session.id)
                async for evt in cls._mock_functional(session, user_content):
                    yield evt
            elif gen_type == GenType.api_base and api_test_gen_use_mock():
                _log.info("[SSE] 使用 Mock 模式 (api_base) session=%s", session.id)
                async for evt in cls._mock_api(session, user_content):
                    yield evt
            elif not is_llm_configured():
                _log.error("[SSE] ❌ LLM 未配置 session=%s", session.id)
                await SessionLifecycleService.mark_failed(session, LLM_NOT_CONFIGURED_MSG)
                yield _sse("error", {"message": LLM_NOT_CONFIGURED_MSG})
            else:
                _log.info("[SSE] 🔄 开始流式执行 Agent session=%s", session.id)
                async for evt in cls._stream_agent(session, user_content, gen_type=gen_type):
                    yield evt
                _log.info("[SSE] ✅ Agent 执行完成 session=%s", session.id)
            
            _log.info("[SSE] 发送 payload_updated 事件 session=%s", session.id)
            yield _sse("payload_updated", {"session_id": session.id})
            
            _log.info("[SSE] 发送 done 事件 session=%s", session.id)
            yield _sse("done", {})
            
            _log.info("[SSE] ✅ _stream_turn 完成 session=%s", session.id)
            
        except asyncio.TimeoutError:
            timeout_msg = f"Agent 执行超时（{_AGENT_TIMEOUT_SECONDS}秒），请稍后重试"
            _log.error("[SSE] ❌ 超时 session=%s: %s", session.id, timeout_msg)
            await SessionLifecycleService.mark_failed(session, timeout_msg)
            yield _sse("error", {"message": timeout_msg})
        except Exception as exc:
            msg = str(exc) or repr(exc)
            _log.error("[SSE] ❌ session=%s 异常: %s", session.id, exc, exc_info=True)
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
            {"points": payload["test_points"], "cases": payload["cases"]},
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
        """使用 asyncio.Queue 桥接后台线程与异步生成器，实现实时流式转发。

        架构：
          主事件循环 (async generator yield SSE)
            ^ asyncio.Queue.get() (异步读取)
          ====================================
          后台线程 (同步执行 agent.stream())
            | queue.put_nowait() (同步写入)

        每个 agent 事件在产生后立即通过 Queue 转发到 async generator，
        前端可以实时收到 custom / messages / tool_call 等 SSE 事件。
        """
        _log.info("[SSE] 🚀 _stream_agent 开始 session=%s, gen_type=%s", session.id, gen_type)
        
        from agents.case_generate_agent import AgentManage
        from agents.memory.manager import RuntimeContext
        from mcp_tools.tools import register_main_loop

        # 注册主事件循环引用，供工具函数中的 DB 操作使用
        register_main_loop(asyncio.get_event_loop())
        _log.info("[SSE] 主事件循环已注册 session=%s", session.id)

        project_name = await SessionLifecycleService.get_project_name(session.project_id)
        thread_prefix = "functional" if gen_type == GenType.functional else "api"
        context = RuntimeContext(
            project_name=project_name,
            module_id=str(session.module_id or ""),
            user_id=str(session.created_by_id),
            session_id=str(session.id),
            thread_id=f"{thread_prefix}-{session.id}",
        )
        _log.info("[SSE] RuntimeContext 已创建 session=%s, thread_id=%s", session.id, context.thread_id)
        
        if gen_type == GenType.functional:
            agent = AgentManage.create_case_generate_agent()
            _log.info("[SSE] 创建 functional agent session=%s", session.id)
        else:
            agent = AgentManage.create_api_case_generate_agent()
            _log.info("[SSE] 创建 api agent session=%s", session.id)

        run_config = {
            "configurable": {
                "thread_id": context.thread_id,
                "ai_session_id": session.id,
            }
        }
        _log.info("[SSE] run_config 已创建 session=%s", session.id)

        assistant_buffer: list[str] = []

        # Tool name -> (icon, stage_text) mapping
        _stage_map = {
            "search_requirement": ("🔍", "正在检索需求文档..."),
            "search_api_document": ("🔍", "正在检索接口文档..."),
            "generate_testcases": ("🧪", "正在生成测试用例..."),
            "generate_base_cases": ("🧪", "正在生成接口测试用例..."),
        }

        # 用于检测阶段转换，在阶段间发送等待提示
        _last_tool_name = None
        _stage_transition_sent = False

        # ===== 使用 Queue 实现实时流式转发 =====
        queue: asyncio.Queue[dict | None] = asyncio.Queue()
        _agent_error: list[Exception | None] = [None]
        event_count = 0

        def _run_in_thread():
            """后台线程：同步执行 agent.stream()，将每个事件立即写入 Queue"""
            nonlocal event_count
            try:
                _log.info("[Agent] session=%s 开始执行 agent_stream(), gen_type=%s", session.id, gen_type)
                for event in AgentManage.agent_chat(
                    agent,
                    user_content,
                    context,
                    run_config=run_config,
                ):
                    # 立即放入队列，不等待收集完毕
                    event_count += 1
                    _log.info("[Agent] session=%s 产生事件 #%s: %s", session.id, event_count, str(event)[:100])
                    queue.put_nowait(event)
                # 发送哨兵值表示结束
                _log.info("[Agent] session=%s 所有事件已放入队列，共 %s 个事件", session.id, event_count)
                queue.put_nowait(None)
                _log.info("[Agent] session=%s agent_stream() 正常结束", session.id)
            except Exception as e:
                _log.error("[Agent] ❌ session=%s agent_stream() 异常: %s", session.id, e, exc_info=True)
                _agent_error[0] = e
                queue.put_nowait(None)  # 确保发送哨兵值

        # 启动后台线程执行 agent
        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()

        # 在异步生成器中逐个从队列取事件并转发为 SSE
        _log.info("[SSE] 🔄 开始处理队列 session=%s", session.id)
        queue_item_count = 0
        
        while True:
            try:
                _log.info("[SSE] ⏳ 等待队列事件 session=%s...", session.id)
                item = await asyncio.wait_for(queue.get(), timeout=_AGENT_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                _log.error("[SSE] ❌ 超时 session=%s", session.id)
                raise TimeoutError(f"Agent 执行超时（{_AGENT_TIMEOUT_SECONDS}秒）")

            queue_item_count += 1
            _log.info("[SSE] 📦 收到队列事件 #%s session=%s", queue_item_count, session.id)

            # 哨兵值：agent 执行完毕（正常或异常）
            if item is None:
                _log.info("[SSE] ✅ 收到哨兵值，结束队列处理 session=%s, 共处理 %s 个事件", session.id, queue_item_count)
                break

            kind = item.get("type")
            content = item.get("content", "")
            _log.info("[SSE] 事件类型: %s, content长度: %s session=%s", kind, len(str(content)), session.id)

            if kind == "custom":
                _log.info("[SSE] 处理 custom 事件: %s... session=%s", str(content)[:50], session.id)
                await MessageService.append(
                    session.id,
                    role=MessageRole.tool,
                    content=str(content),
                    message_type=MessageType.custom,
                )
                yield _sse("custom", str(content))
                _log.info("[SSE] ✅ custom 事件已发送 session=%s", session.id)
            elif kind == "messages":
                assistant_buffer.append(str(content))
                # LLM token 流实时推送
                _log.info("[SSE] 处理 messages 事件: %s chars session=%s", len(str(content)), session.id)
                yield _sse("messages", str(content))
            elif kind == "tool_call":
                tool_name = item.get("tool_name") or ""
                _log.info("[SSE] 处理 tool_call 事件: %s session=%s", tool_name, session.id)
                
                stage_info = _stage_map.get(tool_name)
                
                # 检测阶段转换：如果工具名称变化，发送阶段间等待提示
                if _last_tool_name is not None and _last_tool_name != tool_name:
                    # 上一个阶段完成，当前阶段即将开始
                    last_stage_info = _stage_map.get(_last_tool_name)
                    if last_stage_info:
                        transition_msg = f"✅ {last_stage_info[1]} 阶段完成，正在准备下一阶段，请稍候..."
                        _log.info("[Agent] 阶段转换: %s -> %s, 发送等待消息: %s", _last_tool_name, tool_name, transition_msg)
                        yield _sse("custom", transition_msg)
                
                if stage_info:
                    icon, stage_text = stage_info
                    stage_msg = f"{icon} {stage_text}"
                    _log.info("[SSE] 发送 stage 事件: %s session=%s", stage_msg, session.id)
                    yield _sse("stage", {"name": tool_name, "text": stage_msg, "status": "running"})
                    yield _sse("custom", stage_msg)
                    await MessageService.append(
                        session.id,
                        role=MessageRole.tool,
                        content=stage_msg,
                        message_type=MessageType.custom,
                    )
                    _stage_transition_sent = False  # 新阶段开始，重置标志
                
                _last_tool_name = tool_name  # 更新上一个工具名称
                
                await MessageService.append(
                    session.id,
                    role=MessageRole.tool,
                    content=str(content),
                    message_type=MessageType.tool_call,
                    tool_name=tool_name,
                )
                _log.info("[SSE] 发送 tool_call 事件: %s session=%s", tool_name, session.id)
                yield _sse("tool_call", {"name": tool_name, "content": content})
                _log.info("[SSE] ✅ tool_call 事件已发送 session=%s", session.id)

        # 如果线程中有异常，重新抛出
        if _agent_error[0] is not None:
            raise _agent_error[0]

        # 保存 assistant 最终消息
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
