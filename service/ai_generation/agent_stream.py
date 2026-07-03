"""Stream Agent turns as SSE events and persist messages."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
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
        _log.info("[SSE-TIME] _stream_turn started session=%s gen_type=%s", session.id, gen_type)

        await MessageService.append(
            session.id,
            role=MessageRole.user,
            content=user_content,
            message_type=MessageType.text,
        )
        await SessionLifecycleService.mark_running(session)

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
                if gen_type == GenType.functional:
                    doc_context = (session.output_payload or {}).get("_document_context", "")
                    has_doc = session.knowledge_document_id is not None and bool(doc_context)
                    if not has_doc:
                        _log.info("[SSE] 无关联需求文档，发送初始 stage session=%s", session.id)
                        yield _sse("stage", {
                            "name": "generate_testcases",
                            "status": "running",
                            "text": "正在分析需求并生成测试用例...",
                        })

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
        from service.core.async_utils import register_main_loop

        # 注册主事件循环引用，供后台线程中的协程调度使用
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
            has_doc = session.knowledge_document_id is not None and bool(
                (session.output_payload or {}).get("_document_context", "")
            )
            if has_doc:
                agent = AgentManage.create_case_generate_agent()
                _log.info("[SSE] 创建 functional agent (有文档) session=%s", session.id)
            else:
                agent = AgentManage.create_functional_generate_agent()
                _log.info("[SSE] 创建 functional agent (无文档，跳过搜索) session=%s", session.id)
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
        _main_loop = asyncio.get_event_loop()

        async def _finalize():
            """线程结束后最终化：保存消息 + 更新 session 状态。"""
            try:
                if _agent_error[0] is not None:
                    await SessionLifecycleService.mark_failed(session, str(_agent_error[0]))
                    return
                if assistant_buffer:
                    await MessageService.append(
                        session.id,
                        role=MessageRole.assistant,
                        content="".join(assistant_buffer),
                        message_type=MessageType.text,
                    )
                refreshed = await AIGenerationSession.get_or_none(id=session.id)
                if refreshed and refreshed.status not in (SessionStatus.success, SessionStatus.confirming) and refreshed.output_payload:
                    refreshed.status = SessionStatus.confirming
                    refreshed.finished_at = datetime.now(timezone.utc)
                    await refreshed.save(update_fields=["status", "finished_at"])
            except Exception as e:
                _log.error("[Agent] _finalize error session=%s: %s", session.id, e, exc_info=True)

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
                _log.info("[Agent] session=%s 所有事件已放入队列，共 %s 个事件", session.id, event_count)
            except Exception as e:
                _log.error("[Agent] ❌ session=%s agent_stream() 异常: %s", session.id, e, exc_info=True)
                _agent_error[0] = e
            finally:
                queue.put_nowait(None)  # 哨兵值
                # 最终化在事件循环中执行（不依赖 SSE 生成器是否存活）
                asyncio.run_coroutine_threadsafe(_finalize(), _main_loop)
                _log.info("[Agent] session=%s agent_stream() 结束，已调度最终化", session.id)

        # 启动后台线程执行 agent
        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()

        # 在异步生成器中逐个从队列取事件并转发为 SSE
        queue_item_count = 0

        try:
            while True:
                try:
                    # 短超时循环：每 100ms 释放 event loop，避免阻塞其他请求
                    # 同时保持总体超时（_AGENT_TIMEOUT_SECONDS）防止无限等待
                    _queue_deadline = time.monotonic() + _AGENT_TIMEOUT_SECONDS
                    while True:
                        _remaining = _queue_deadline - time.monotonic()
                        if _remaining <= 0:
                            raise TimeoutError(f"Agent 执行超时（{_AGENT_TIMEOUT_SECONDS}秒）")
                        try:
                            item = await asyncio.wait_for(queue.get(), timeout=min(0.1, _remaining))
                            break
                        except asyncio.TimeoutError:
                            continue
                except TimeoutError:
                    _log.error("[SSE] ❌ 超时 session=%s", session.id)
                    raise

                queue_item_count += 1
                _log.info("[SSE] 📦 收到队列事件 #%s session=%s", queue_item_count, session.id)

                # 哨兵值：agent 执行完毕（正常或异常）
                if item is None:
                    _log.info("[SSE] sentinel received, ending queue loop session=%s, events=%s", session.id, queue_item_count)
                    break

                kind = item.get("type")
                content = item.get("content", "")
                _log.info("[SSE] 事件类型: %s, content长度: %s session=%s", kind, len(str(content)), session.id)

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
                    yield _sse("tool_call", {"name": tool_name, "content": content})

        except (GeneratorExit, asyncio.CancelledError):
            _log.info("[SSE-TIME] GeneratorExit/CancelledError session=%s", session.id)
            return
