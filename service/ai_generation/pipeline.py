"""Multi-interface deterministic pipeline for API case generation.

Replaces the ReAct agent for the new multi-interface flow:
  Phase 1: Parse doc + create interfaces (Mode 1 only)
  Phase 2/1: Generate base cases per interface
  Phase 3/2: Present cards for user editing
  --- user edits & saves ---
  Phase 4/3: Generate structured cases
  Phase 5/4: Pre-execute + summary
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from service.ai_generation.event_buffer import (
    claim_live_queue,
    cleanup_buffer,
    cleanup_live_queue,
    get_or_create_buffer,
    register_live_queue,
)
from service.ai_generation.models import AIGenerationSession
from service.core.enums import SessionStatus
from tortoise.functions import Max

_log = logging.getLogger("agent_pipeline")


def _sse(event: str, data: Any) -> str:
    import json as _json
    payload = _json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else _json.dumps(str(data), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


class ApiAgentPipeline:
    """Multi-interface deterministic pipeline."""

    # 保持后台 Task 的强引用，防止 GC 回收导致 Task 被取消
    _running_tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------
    # Phase 1-3: Initial generation (SSE Stream 1)
    # ------------------------------------------------------------------
    @classmethod
    async def run_phase_1_to_3(
        cls,
        session: AIGenerationSession,
        *,
        mode: str,
        user_prompt: str | None,
        interface_ids: list[int] | None,
        api_doc_text: str | None,
    ) -> AsyncIterator[str]:
        """SSE Stream 1: Phase 1 -> 2 -> 3.

        解耦架构：实际执行在 asyncio.Task 中后台运行，
        SSE 生成器仅从 Queue 读取事件转发。客户端断开时
        Task 继续执行并完成 DB 更新，用户回来后可通过
        reconnect 端点重放缓冲事件并接入实时队列。
        """
        queue: asyncio.Queue = asyncio.Queue()
        buf = get_or_create_buffer(session.id)
        register_live_queue(session.id, queue)

        task = asyncio.create_task(
            cls._execute_phase_1_to_3(
                session, queue,
                mode=mode,
                user_prompt=user_prompt,
                interface_ids=interface_ids,
                api_doc_text=api_doc_text,
            )
        )
        # 保持强引用，防止 generator 退出后 Task 被 GC 回收取消
        cls._running_tasks.add(task)
        task.add_done_callback(cls._running_tasks.discard)
        try:
            while True:
                item = await queue.get()
                if item is None:  # 哨兵值
                    break
                yield item
                # 缓冲已发送的事件，供断线重连时重放
                event_type = item.split("\n", 1)[0].replace("event: ", "") if item.startswith("event: ") else "unknown"
                buf.append(item, event_type)
        except (GeneratorExit, asyncio.CancelledError):
            _log.info("[pipeline] Phase 1-3 SSE 客户端断开 session=%s，后台任务继续执行", session.id)
            return  # Task 继续运行，不取消
        finally:
            cleanup_live_queue(session.id)

    @classmethod
    async def _execute_phase_1_to_3(
        cls,
        session: AIGenerationSession,
        queue: asyncio.Queue,
        *,
        mode: str,
        user_prompt: str | None,
        interface_ids: list[int] | None,
        api_doc_text: str | None,
    ) -> None:
        """后台执行 Phase 1-3，事件写入 Queue，完成后更新 DB。"""
        try:
            payload = dict(session.output_payload or {})
            payload["mode"] = mode
            payload["user_prompt"] = user_prompt or ""
            payload["interfaces"] = []
            payload["pipeline_progress"] = cls._init_progress(mode, current_phase=1)

            session.status = SessionStatus.running
            session.output_payload = payload
            await session.save(update_fields=["status", "output_payload"])

            # 持久化用户输入消息（供历史记录回放）
            from service.ai_generation.message_service import MessageService
            from service.core.enums import MessageRole, MessageType
            if user_prompt:
                await MessageService.append(
                    session.id,
                    role=MessageRole.user,
                    content=user_prompt,
                    message_type=MessageType.text,
                )

            # -- Phase 1: Create interfaces (Mode 1 only) --
            if mode in ("from_doc", "from_prompt") and api_doc_text:
                await queue.put(_sse("stage", {
                    "name": "create_interfaces",
                    "status": "running",
                    "text": "正在解析接口文档...",
                }))
                interfaces_data = await cls._phase1_create_interfaces(
                    session, api_doc_text
                )
                payload["interfaces"] = interfaces_data
                await queue.put(_sse("stage", {
                    "name": "create_interfaces",
                    "status": "done",
                    "text": f"解析完成，共发现 {len(interfaces_data)} 个接口",
                }))
                await MessageService.append(session.id, role=MessageRole.tool, content=f"解析完成，共发现 {len(interfaces_data)} 个接口", message_type=MessageType.custom)
                await queue.put(_sse("pipeline_progress", cls._update_progress(
                    payload["pipeline_progress"], phase=1, status="done"
                )))
            elif mode == "from_interfaces" and interface_ids:
                # Load existing interfaces
                interfaces_data = await cls._load_existing_interfaces(interface_ids, session.project_id)
                payload["interfaces"] = interfaces_data
                # Skip phase 1
                await queue.put(_sse("pipeline_progress", cls._update_progress(
                    payload["pipeline_progress"], phase=1, status="done"
                )))

            # -- Phase 2/1: Generate base cases per interface --
            await queue.put(_sse("stage", {
                "name": "generate_base_cases",
                "status": "running",
                "text": "正在为各接口生成基础用例...",
            }))
            await MessageService.append(session.id, role=MessageRole.tool, content="正在为各接口生成基础用例...", message_type=MessageType.custom)

            for i, iface in enumerate(payload["interfaces"]):
                await queue.put(_sse("custom", f"正在为「{iface.get('summary', '')}」生成基础用例..."))
                try:
                    base_cases = await cls._generate_base_cases_for_interface(
                        iface, user_prompt, session.project_id
                    )
                    iface["base_cases"] = base_cases
                    iface["selected_indexes"] = list(range(len(base_cases)))
                    await queue.put(_sse("custom", f"✅ 「{iface.get('summary', '')}」生成 {len(base_cases)} 条基础用例"))
                    await MessageService.append(session.id, role=MessageRole.tool, content=f"✅ 「{iface.get('summary', '')}」生成 {len(base_cases)} 条基础用例", message_type=MessageType.custom)
                    await queue.put(_sse("interface_progress", {
                        "interface_index": i,
                        "phase": "base_cases_done",
                        "case_count": len(base_cases),
                    }))
                except Exception as e:
                    _log.error("基础用例生成失败 [%s]: %s", iface.get("summary"), e, exc_info=True)
                    iface["base_cases"] = []
                    iface["selected_indexes"] = []
                    iface["error"] = str(e)
                    await queue.put(_sse("custom", f"❌ 「{iface.get('summary', '')}」生成失败: {str(e)[:100]}"))
                    await MessageService.append(session.id, role=MessageRole.tool, content=f"❌ 「{iface.get('summary', '')}」生成失败: {str(e)[:100]}", message_type=MessageType.custom)

            await queue.put(_sse("stage", {
                "name": "generate_base_cases",
                "status": "done",
                "text": "基础用例生成完毕",
            }))
            await MessageService.append(session.id, role=MessageRole.tool, content="基础用例生成完毕", message_type=MessageType.custom)
            await queue.put(_sse("pipeline_progress", cls._update_progress(
                payload["pipeline_progress"], phase=2, status="done"
            )))

            # -- Phase 3/2: Present cards --
            # Check if any interface actually generated base cases
            has_any_cases = any(iface.get("base_cases") for iface in payload.get("interfaces", []))

            # Save payload to DB
            session.output_payload = payload
            if has_any_cases:
                session.status = SessionStatus.confirming
            else:
                # All interfaces failed — mark session as failed, not confirming
                session.status = SessionStatus.failed
                session.error_message = "所有接口的基础用例生成均失败，请检查 LLM 配置或重试"
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["output_payload", "status", "finished_at", "error_message"])

            if not has_any_cases:
                await queue.put(_sse("error", {"message": session.error_message}))
                await queue.put(_sse("done", {}))
                return

            await queue.put(_sse("stage", {
                "name": "edit_base_cases",
                "status": "running",
                "text": "请检查并编辑基础用例",
            }))
            await MessageService.append(session.id, role=MessageRole.tool, content="请检查并编辑基础用例", message_type=MessageType.custom)
            await queue.put(_sse("pipeline_progress", cls._update_progress(
                payload["pipeline_progress"], phase=3, status="running"
            )))
            await queue.put(_sse("payload_updated", {}))
            await queue.put(_sse("done", {}))

        except Exception as e:
            _log.error("Pipeline phase 1-3 failed: %s", e, exc_info=True)
            try:
                await MessageService.append(session.id, role=MessageRole.tool, content=f"❌ 生成失败: {str(e)[:200]}", message_type=MessageType.custom)
            except Exception:
                pass
            try:
                refreshed = await AIGenerationSession.get_or_none(id=session.id)
                if refreshed:
                    refreshed.status = SessionStatus.failed
                    refreshed.error_message = str(e)
                    refreshed.finished_at = datetime.now(timezone.utc)
                    await refreshed.save(update_fields=["status", "error_message", "finished_at"])
            except Exception as db_err:
                _log.error("Phase 1-3 更新失败状态时出错: %s", db_err)
            await queue.put(_sse("error", {"message": str(e)}))
            await queue.put(_sse("done", {}))
        finally:
            await queue.put(None)  # 哨兵值，通知 SSE reader 结束

    # ------------------------------------------------------------------
    # Phase 4-5: Structuring + execution (SSE Stream 2)
    # ------------------------------------------------------------------
    @classmethod
    async def run_phase_4_to_5(
        cls,
        session: AIGenerationSession,
        *,
        environment_id: int | None,
    ) -> AsyncIterator[str]:
        """SSE Stream 2: Phase 4 -> 5 + summary.

        解耦架构：实际执行在 asyncio.Task 中后台运行，
        SSE 生成器仅从 Queue 读取事件转发。客户端断开时
        Task 继续执行并完成 DB 更新。
        """
        queue: asyncio.Queue = asyncio.Queue()
        buf = get_or_create_buffer(session.id)
        register_live_queue(session.id, queue)

        task = asyncio.create_task(
            cls._execute_phase_4_to_5(session, queue, environment_id)
        )
        # 保持强引用，防止 generator 退出后 Task 被 GC 回收取消
        cls._running_tasks.add(task)
        task.add_done_callback(cls._running_tasks.discard)
        try:
            while True:
                item = await queue.get()
                if item is None:  # 哨兵值
                    break
                yield item
                event_type = item.split("\n", 1)[0].replace("event: ", "") if item.startswith("event: ") else "unknown"
                buf.append(item, event_type)
        except (GeneratorExit, asyncio.CancelledError):
            _log.info("[pipeline] Phase 4-5 SSE 客户端断开 session=%s，后台任务继续执行", session.id)
            return  # Task 继续运行，不取消
        finally:
            cleanup_live_queue(session.id)

    # ------------------------------------------------------------------
    # Reconnect: Replay buffered events + attach to live queue
    # ------------------------------------------------------------------
    @classmethod
    async def stream_reconnect(
        cls,
        session: AIGenerationSession,
        last_seq: int = -1,
    ) -> AsyncIterator[str]:
        """SSE reconnect stream: replay buffered events, then attach to live queue.

        Called when the frontend returns to a session that may still be running.
        - Replays events from the buffer (skipping those already seen via last_seq)
        - If the task is still running, attaches to the live queue for new events
        - Always ends with a 'done' event so the frontend knows the replay is complete
        """
        from service.ai_generation.event_buffer import get_buffer, claim_live_queue

        buf = get_buffer(session.id)
        live_queue = claim_live_queue(session.id)

        # Phase 1: Replay buffered events
        if buf:
            missed = buf.replay_from(last_seq)
            _log.info("[reconnect] Replaying %d buffered events for session=%s (from seq=%d)",
                       len(missed), session.id, last_seq)
            for event in missed:
                yield event.sse_str

        # Phase 2: Attach to live queue if task is still running
        if live_queue:
            _log.info("[reconnect] Attaching to live queue for session=%s", session.id)
            try:
                while True:
                    try:
                        item = await asyncio.wait_for(live_queue.get(), timeout=30)
                    except asyncio.TimeoutError:
                        # Send heartbeat to keep connection alive
                        yield _sse("heartbeat", {})
                        continue
                    if item is None:  # sentinel: task completed
                        break
                    yield item
            except (GeneratorExit, asyncio.CancelledError):
                _log.info("[reconnect] Client disconnected during live stream session=%s", session.id)
                return

        # Always send done so frontend knows the reconnect stream is complete
        yield _sse("done", {"reconnected": True})

    @classmethod
    async def _execute_phase_4_to_5(
        cls,
        session: AIGenerationSession,
        queue: asyncio.Queue,
        environment_id: int | None,
    ) -> None:
        """后台执行 Phase 4-5，事件写入 Queue，完成后更新 DB。"""
        try:
            payload = dict(session.output_payload or {})
            interfaces = payload.get("interfaces", [])

            session.status = SessionStatus.running
            session.finished_at = None
            await session.save(update_fields=["status", "finished_at"])

            # -- Phase 4/3: Generate structured cases --
            await queue.put(_sse("stage", {
                "name": "structure_cases",
                "status": "running",
                "text": "正在生成结构化测试用例...",
            }))

            from service.api_test.case.generation_service import ApiCaseGenerationService

            for i, iface in enumerate(interfaces):
                selected_indexes = iface.get("selected_indexes", [])
                base_cases = iface.get("base_cases", [])
                if not selected_indexes or not base_cases:
                    continue

                await queue.put(_sse("custom", f"正在为「{iface.get('summary', '')}」生成结构化用例..."))

                selected_items = [
                    (idx, base_cases[idx])
                    for idx in selected_indexes
                    if idx < len(base_cases) and isinstance(base_cases[idx], dict)
                ]

                if not selected_items:
                    continue

                # Log selected case titles for clarity
                selected_titles = [f"[{idx}] {base.get('name', '未命名')}" for idx, base in selected_items]
                selected_msg = f"用户选择了 {len(selected_items)} 条用例进行结构化: {', '.join(selected_titles)}"
                await queue.put(_sse("custom", selected_msg))
                iface["selected_titles_text"] = selected_msg

                # Debug: log the edited base cases before structuring
                for idx, base in selected_items:
                    _log.info(
                        "[pipeline] 结构化前 base_case[%d]: name=%s, expected=%s",
                        idx, base.get("name"), base.get("expected")
                    )

                try:
                    # Build interface doc for structuring
                    api_doc = iface.get("api_doc", "")
                    if isinstance(api_doc, dict):
                        api_doc = json.dumps(api_doc, ensure_ascii=False)

                    # Load precondition docs
                    precoditions_api_doc = await cls._load_preconditions(
                        iface, session.project_id
                    )

                    # Enrich precondition docs from DB (same as confirm flow)
                    precoditions_api_doc = await ApiCaseGenerationService.enrich_preconditions_api_doc(
                        session.project_id, selected_items, precoditions_api_doc
                    )

                    # Load environment data for LLM variable references (same as confirm flow)
                    test_env_data = None
                    if environment_id:
                        from service.test_execution.env_loader import load_test_env_data
                        test_env_data = await load_test_env_data(environment_id)

                    # Run structuring (skip_execution=True)
                    pre_run_results = await ApiCaseGenerationService._pre_run_selected_base_cases(
                        selected_items=selected_items,
                        api_doc=api_doc,
                        precoditions_api_doc=precoditions_api_doc,
                        environment_id=environment_id or 0,
                        project_id=session.project_id,
                        test_env_data=test_env_data,
                        skip_execution=True,
                    )

                    iface["structured_cases"] = [r.api_case for r in pre_run_results if r.api_case]
                    iface["structured_count"] = len(iface["structured_cases"])
                    await queue.put(_sse("custom", f"✅ 「{iface.get('summary', '')}」结构化完成: {len(iface['structured_cases'])} 条"))

                    # --- Precondition handling (same logic as interface detail page) ---
                    # 1. Collect AI-generated precondition steps
                    ai_precondition_map: dict[str, dict] = {}
                    for r in pre_run_results:
                        if not isinstance(r.api_case, dict):
                            continue
                        for pre in (r.api_case.get("preconditions") or []):
                            if not isinstance(pre, dict):
                                continue
                            title = (pre.get("title") or "").strip()
                            if title and title not in ai_precondition_map:
                                ai_precondition_map[title] = pre

                    # 2. Align variable names across distributed LLM outputs
                    if ai_precondition_map:
                        _log.info("[pipeline] 调用 _align_variable_names: precondition_titles=%s, pre_run_count=%d",
                                  list(ai_precondition_map.keys()), len(pre_run_results))
                        ApiCaseGenerationService._align_variable_names(
                            ai_precondition_map, pre_run_results
                        )

                    # 3. Create precondition test cases in DB
                    precondition_map: dict[str, int] = {}
                    interface_id = iface.get("interface_id")
                    if interface_id and ai_precondition_map:
                        _log.info("[pipeline] ai_precondition_map keys: %s", list(ai_precondition_map.keys()))
                        from service.api_test.interface.models import ApiInterface
                        iface_obj = await ApiInterface.get_or_none(id=interface_id)
                        if iface_obj:
                            precondition_map = await ApiCaseGenerationService._create_precondition_cases(
                                interface=iface_obj,
                                base_cases=base_cases,
                                selected_indexes=[idx for idx, _ in selected_items],
                                precoditions_api_doc=precoditions_api_doc,
                                environment_id=environment_id,
                                test_env_data=None,
                                user_id=session.created_by_id,
                                session_id=session.id,
                                ai_precondition_map=ai_precondition_map,
                            )
                            _log.info("[pipeline] precondition_map created: %s", precondition_map)

                    # 4. Save to DB (create ApiBaseCase + ApiTestCase records)
                    if interface_id:
                        created_ids = await cls._save_cases_to_db(
                            session, iface, selected_items, pre_run_results,
                            interface_id, precondition_map, environment_id
                        )
                        iface["created_case_ids"] = created_ids

                except Exception as e:
                    _log.error("结构化失败 [%s]: %s", iface.get("summary"), e, exc_info=True)
                    iface["structured_cases"] = []
                    iface["structure_error"] = str(e)
                    await queue.put(_sse("custom", f"❌ 「{iface.get('summary', '')}」结构化失败: {str(e)[:100]}"))

                await queue.put(_sse("interface_progress", {
                    "interface_index": i,
                    "phase": "structured_done",
                    "structured_count": iface.get("structured_count", 0),
                    "structure_error": iface.get("structure_error"),
                }))

            await queue.put(_sse("stage", {
                "name": "structure_cases",
                "status": "done",
                "text": "结构化用例生成完毕",
            }))

            # -- Phase 5/4: Pre-execute --
            if environment_id:
                _log.info("[pipeline] 开始预执行阶段, environment_id=%s, 接口数量=%d", environment_id, len(interfaces))
                await queue.put(_sse("stage", {
                    "name": "pre_run",
                    "status": "running",
                    "text": "正在预执行测试用例...",
                }))

                for i, iface in enumerate(interfaces):
                    case_ids = iface.get("created_case_ids", [])
                    _log.info("[pipeline] 接口 %d/%d: summary=%s, case_ids=%s",
                             i+1, len(interfaces), iface.get("summary"), case_ids)
                    if not case_ids:
                        _log.info("[pipeline] 接口 %d 没有 case_ids，跳过", i+1)
                        continue
                    await queue.put(_sse("custom", f"正在预执行「{iface.get('summary', '')}」的用例..."))
                    try:
                        _log.info("[pipeline] 开始执行接口 %d 的用例", i+1)
                        exec_results = await cls._execute_cases(
                            case_ids, environment_id, session.created_by_id
                        )
                        _log.info("[pipeline] 接口 %d 执行完成: %s", i+1, exec_results)
                        iface["exec_results"] = exec_results
                        await queue.put(_sse("custom", f"✅ 「{iface.get('summary', '')}」预执行完成: "
                                  f"通过率 {exec_results.get('pass_rate', 0):.0%}"))
                    except Exception as e:
                        _log.error("预执行失败 [%s]: %s", iface.get("summary"), e, exc_info=True)
                        iface["exec_results"] = {"total": len(case_ids), "passed": 0, "failed": 0, "error": 0, "pass_rate": 0}
                        await queue.put(_sse("custom", f"❌ 「{iface.get('summary', '')}」预执行失败"))

                    await queue.put(_sse("interface_progress", {
                        "interface_index": i,
                        "phase": "exec_done",
                        "exec_results": iface.get("exec_results", {}),
                    }))

                _log.info("[pipeline] 预执行阶段完成，准备发送 stage done 消息")
                await queue.put(_sse("stage", {
                    "name": "pre_run",
                    "status": "done",
                    "text": "预执行完毕",
                }))
                _log.info("[pipeline] stage done 消息已发送")

                # -- Sync debug templates from pre-execution results --
                try:
                    _log.info("[pipeline] 开始同步调试模板...")
                    await cls._sync_debug_templates(interfaces)
                    _log.info("[pipeline] 调试模板同步完成")
                except Exception as e:
                    _log.error("[pipeline] 同步调试模板失败: %s", e, exc_info=True)
            else:
                _log.info("[pipeline] 跳过预执行阶段: environment_id 为空")

            # -- Summary --
            summary = cls._build_summary(interfaces)
            payload["summary"] = summary
            payload["pipeline_progress"] = cls._finalize_progress(payload.get("pipeline_progress", {}))

            session.output_payload = payload
            session.status = SessionStatus.success
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["output_payload", "status", "finished_at"])

            # 自动生成标题（fire-and-forget，不阻塞 pipeline）
            from service.ai_generation.session_lifecycle import SessionLifecycleService
            asyncio.create_task(SessionLifecycleService.auto_summarize_title(session.id))

            # 持久化关键阶段消息到数据库，供历史记录回放
            from service.ai_generation.message_service import MessageService
            from service.core.enums import MessageRole, MessageType
            stage_logs = []
            for iface in interfaces:
                name = iface.get("summary", "")
                sc = iface.get("structured_count", 0)
                er = iface.get("exec_results", {})
                sel_text = iface.get("selected_titles_text", "")
                if sel_text:
                    stage_logs.append(f"「{name}」{sel_text}")
                stage_logs.append(f"✅ 「{name}」结构化 {sc} 条")
                if er:
                    pr = er.get("pass_rate", 0)
                    stage_logs.append(f"{'✅' if pr == 1 else '❌'} 「{name}」预执行通过率 {pr:.0%}")
            summary_text = (
                f"生成完成：共 {summary['total_interfaces']} 个接口，"
                f"{summary['total_cases']} 条用例，"
                f"整体通过率 {summary['overall_pass_rate']:.0%}\n"
                + "\n".join(stage_logs)
            )
            await MessageService.append(
                session.id,
                role=MessageRole.assistant,
                content=summary_text,
                message_type=MessageType.text,
            )
            for log_line in stage_logs:
                await MessageService.append(
                    session.id,
                    role=MessageRole.tool,
                    content=log_line,
                    message_type=MessageType.custom,
                )

            await queue.put(_sse("summary", summary))
            await queue.put(_sse("payload_updated", {}))
            await queue.put(_sse("done", {}))

        except Exception as e:
            _log.error("Pipeline phase 4-5 failed: %s", e, exc_info=True)
            try:
                refreshed = await AIGenerationSession.get_or_none(id=session.id)
                if refreshed:
                    refreshed.status = SessionStatus.failed
                    refreshed.error_message = str(e)
                    refreshed.finished_at = datetime.now(timezone.utc)
                    await refreshed.save(update_fields=["status", "error_message", "finished_at"])
            except Exception as save_err:
                _log.error("Failed to save error status: %s", save_err)
            await queue.put(_sse("error", {"message": str(e)}))
            await queue.put(_sse("done", {}))
        finally:
            await queue.put(None)  # 哨兵值：通知 stream 结束

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    async def _phase1_create_interfaces(
        cls, session: AIGenerationSession, api_doc_text: str
    ) -> list[dict]:
        """Parse API doc and create interfaces in DB. Returns interface data list."""
        from service.ai_engine.parsers.api_document_ai_parser import APIDocumentParser

        # FIX: 使用 asyncio.to_thread 将同步 LLM 调用放到后台线程，避免阻塞 event loop
        parsed = await asyncio.to_thread(APIDocumentParser().api_parser, api_doc_text)
        if not parsed:
            return []
        if isinstance(parsed, dict):
            parsed = [parsed]

        catalog = await cls._get_or_create_ai_catalog(session.project_id)
        interfaces_data = []
        skipped = []

        from service.api_test.interface.models import ApiInterface

        for item in parsed:
            method = (item.get("method") or "GET").upper()
            path = item.get("path") or ""
            summary = item.get("summary") or ""
            if not summary:
                summary = f"{method} {path}"

            # Check duplicate within same catalog
            existing = await ApiInterface.filter(
                project_id=session.project_id,
                catalog_id=catalog.id,
                method=method,
                path=path,
                is_current=True,
            ).first()

            if existing:
                skipped.append(summary or path)
                # Use existing interface
                api_doc_json = json.dumps(item, ensure_ascii=False)
                interfaces_data.append({
                    "index": len(interfaces_data),
                    "interface_id": existing.id,
                    "summary": existing.summary or summary,
                    "method": existing.method,
                    "path": existing.path,
                    "api_doc": api_doc_json,
                    "skipped": True,
                    "base_cases": [],
                    "selected_indexes": [],
                })
                continue

            # Create new interface with auto-incremented version
            from service.api_test.interface.models import ApiInterface as ApiInterfaceModel

            # Get max version for this (project, method, path)
            max_version_result = await ApiInterfaceModel.filter(
                project_id=session.project_id,
                method=method,
                path=path,
            ).annotate(max_version=Max("version")).values("max_version")

            max_version = max_version_result[0]["max_version"] if max_version_result else 0
            new_version = (max_version or 0) + 1

            try:
                iface = await ApiInterface.create(
                    project_id=session.project_id,
                    catalog_id=catalog.id,
                    module_id=session.module_id,
                    method=method,
                    path=path,
                    summary=summary,
                    parameters=item.get("parameters") or {},
                    request_body=item.get("requestBody") or item.get("request_body"),
                    responses=item.get("responses") or {},
                    source="ai",
                    version=new_version,
                    is_current=True,
                    created_by_id=session.created_by_id,
                )
                api_doc_json = json.dumps(item, ensure_ascii=False)
                interfaces_data.append({
                    "index": len(interfaces_data),
                    "interface_id": iface.id,
                    "summary": summary,
                    "method": method,
                    "path": path,
                    "api_doc": api_doc_json,
                    "skipped": False,
                    "base_cases": [],
                    "selected_indexes": [],
                })
            except Exception as e:
                _log.error("创建接口失败 [%s %s]: %s", method, path, e, exc_info=True)

        return interfaces_data

    @classmethod
    async def _load_existing_interfaces(
        cls, interface_ids: list[int], project_id: int
    ) -> list[dict]:
        """Load existing interfaces by IDs and return interface data list."""
        from service.api_test.interface.models import ApiInterface
        from service.api_test.shared.interface_doc import interface_to_doc_dict

        interfaces_data = []
        for iface_id in interface_ids:
            iface = await ApiInterface.get_or_none(id=iface_id, project_id=project_id)
            if not iface:
                continue
            doc_dict = interface_to_doc_dict(iface)
            interfaces_data.append({
                "index": len(interfaces_data),
                "interface_id": iface.id,
                "summary": iface.summary or iface.path,
                "method": iface.method,
                "path": iface.path,
                "api_doc": json.dumps(doc_dict, ensure_ascii=False),
                "skipped": False,
                "base_cases": [],
                "selected_indexes": [],
            })
        return interfaces_data

    @classmethod
    async def _generate_base_cases_for_interface(
        cls, iface_data: dict, user_prompt: str | None, project_id: int
    ) -> list[dict]:
        """Run base case generation workflow for a single interface.

        Uses the same two-layer dependency strategy as the interface detail page:
        1. Try pre-configured dependencies via DependencyResolverService
        2. Fall back to all project interface summaries for LLM auto-detection
        """
        import time as _time
        from service.ai_engine.workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow
        from service.api_test.dependency.resolver_service import DependencyResolverService
        from service.api_test.case.generation_service import ApiCaseGenerationService

        target_summary = iface_data.get("summary", "")

        api_doc = iface_data.get("api_doc", "")
        if isinstance(api_doc, dict):
            api_doc = json.dumps(api_doc, ensure_ascii=False)

        # Layer 1: Get pre-configured dependencies for this interface
        precoditions: list[str] = []
        interface_id = iface_data.get("interface_id")
        if interface_id:
            try:
                resolved = await DependencyResolverService.resolve(interface_id)
                precoditions = resolved.precoditions_summaries or []
            except Exception:
                pass

        # Layer 2: If no pre-configured deps, pass all project interfaces for LLM auto-detection
        if not precoditions:
            precoditions = await ApiCaseGenerationService._get_all_project_interface_summaries(project_id)

        workflow = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
        _t0 = _time.monotonic()
        # FIX: 使用 asyncio.to_thread 将同步 LangGraph invoke 放到后台线程，避免阻塞 event loop
        state = await asyncio.to_thread(workflow.invoke, {
            "api_doc": api_doc,
            "precoditions": precoditions,
            "user_prompt": user_prompt,
        })
        _elapsed = _time.monotonic() - _t0

        raw_cases = state.get("api_cases") if isinstance(state, dict) else None

        base_cases = raw_cases or []

        # 安全网：过滤掉不属于目标接口的用例（LLM 可能错误地为前置依赖接口生成用例）
        if base_cases and precoditions and target_summary:
            base_cases = cls._filter_precondition_cases(base_cases, target_summary, precoditions)

        return base_cases

    @classmethod
    def _filter_precondition_cases(
        cls, cases: list[dict], target_summary: str, precondition_summaries: list[str]
    ) -> list[dict]:
        """过滤掉主要描述前置依赖接口的用例。

        三层防护避免误过滤：
        条件1: pre_summary 长度 ≥ 4（排除过短名称的误匹配）
        条件2: 用例名与前置接口的相似度 > 与目标接口的相似度
        条件3: 用例名包含目标接口的关键字时不过滤
        """

        def _char_similarity(a: str, b: str) -> float:
            """计算两个字符串的字符级相似度（交集 / 较长串长度）"""
            if not a or not b:
                return 0.0
            set_a = set(a)
            set_b = set(b)
            intersection = len(set_a & set_b)
            max_len = max(len(set_a), len(set_b))
            return intersection / max_len if max_len > 0 else 0.0

        def _extract_keywords(summary: str) -> list[str]:
            """从接口名称中提取关键字（2字以上的连续子串）"""
            keywords = []
            # 按常见分隔符拆分
            parts = summary.replace(" ", "").replace("/", "").replace("-", "").replace("_", "")
            # 提取 2-4 字的滑动窗口作为关键字
            for size in range(2, min(5, len(parts) + 1)):
                for i in range(len(parts) - size + 1):
                    kw = parts[i:i + size]
                    if kw not in keywords:
                        keywords.append(kw)
            return keywords

        target_keywords = _extract_keywords(target_summary)

        filtered = []
        for case in cases:
            name = (case.get("name") or "").strip()
            if not name:
                filtered.append(case)
                continue

            # 条件3：用例名包含目标接口的关键字 → 不过滤
            has_target_keyword = any(kw in name for kw in target_keywords if len(kw) >= 2)
            if has_target_keyword:
                filtered.append(case)
                continue

            # 检查用例名称是否主要匹配前置依赖接口
            is_precond_case = False
            for pre_summary in precondition_summaries:
                if not pre_summary:
                    continue

                # 条件1：前置接口名称太短（< 4 字），子串匹配不可靠，跳过
                if len(pre_summary) < 4:
                    continue

                # 原始子串检查
                if pre_summary not in name:
                    continue
                if target_summary in name:
                    continue

                # 条件2：相似度比较 — 用例名必须更像前置接口而非目标接口
                sim_pre = _char_similarity(name, pre_summary)
                sim_target = _char_similarity(name, target_summary)
                if sim_pre <= sim_target:
                    _log.info("[pipeline] 跳过过滤: '%s' 与目标 '%s' 更相似 (%.2f > %.2f)",
                              name, target_summary, sim_target, sim_pre)
                    continue

                is_precond_case = True
                _log.info("[pipeline] 过滤前置依赖用例: '%s' (匹配前置: '%s' sim=%.2f, 目标: '%s' sim=%.2f)",
                          name, pre_summary, sim_pre, target_summary, sim_target)
                break

            if not is_precond_case:
                filtered.append(case)

        return filtered

    @classmethod
    async def _get_or_create_ai_catalog(cls, project_id: int, name: str = "AI生成接口"):
        """Get or create the AI-generated interfaces catalog (root-level)."""
        from service.api_test.interface.models import ApiInterfaceCatalog

        catalog = await ApiInterfaceCatalog.get_or_none(
            project_id=project_id, name=name, parent_id=None
        )
        if not catalog:
            # Get max sort_order at root level
            from tortoise.functions import Max
            result = await ApiInterfaceCatalog.filter(
                project_id=project_id, parent_id=None
            ).annotate(max_sort=Max("sort_order")).first()
            next_order = (getattr(result, 'max_sort', None) or 0) + 1 if result else 0

            catalog = await ApiInterfaceCatalog.create(
                project_id=project_id,
                name=name,
                parent_id=None,
                level=1,
                sort_order=next_order,
            )
        return catalog

    @classmethod
    async def _load_preconditions(cls, iface_data: dict, project_id: int) -> list[dict]:
        """Load precondition API docs for an interface."""
        from service.api_test.dependency.resolver_service import DependencyResolverService

        interface_id = iface_data.get("interface_id")
        if not interface_id:
            return []
        try:
            resolved = await DependencyResolverService.resolve(interface_id)
            return resolved.precoditions_api_doc or []
        except Exception:
            return []

    @classmethod
    async def _save_cases_to_db(cls, session, iface_data, selected_items, pre_run_results,
                                 interface_id, precondition_map=None, environment_id=None):
        """Save base cases and test cases to DB for one interface. Returns list of created case IDs.

        Iterates over pre_run_results (same as confirm flow) to avoid index misalignment.
        """
        from service.api_test.models import ApiBaseCase, ApiTestCase
        from service.api_test.case.generation_service import ApiCaseGenerationService
        from service.core.enums import (
            ApiBaseCaseStatus,
            ApiCaseKind,
            ExecStatus,
            ReviewStatus,
            SourceType,
        )

        base_cases = iface_data.get("base_cases", [])
        created_case_ids = []
        initial_exec_status = ExecStatus.running if environment_id else ExecStatus.pending

        # Verify interface still exists in DB before creating cases
        if interface_id:
            from service.api_test.interface.models import ApiInterface as ApiInterfaceModel
            iface_exists = await ApiInterfaceModel.get_or_none(id=interface_id)
            if not iface_exists:
                _log.warning("[pipeline] 接口不存在，跳过用例创建: interface_id=%s", interface_id)
                return []

        # Iterate over pre_run_results (same as confirm flow)
        for pre_result in pre_run_results:
            idx = pre_result.index
            if idx >= len(base_cases):
                continue
            base = base_cases[idx]

            case_title = str(
                pre_result.api_case.get("title") or base.get("name") or "untitled"
            ) if isinstance(pre_result.api_case, dict) else base.get("name", "untitled")

            # 检查是否已存在同 (interface_id, case_kind, title) 的用例
            if interface_id:
                existing_tc = await ApiTestCase.filter(
                    interface_id=interface_id,
                    case_kind=ApiCaseKind.main,
                    title=case_title,
                ).first()
                if existing_tc:
                    # 用例已存在（可能被测试套件引用），跳过创建，复用已有 id
                    _log.info("[pipeline] 用例已存在，跳过创建: '%s' (id=%s)", case_title, existing_tc.id)
                    created_case_ids.append(existing_tc.id)
                    continue

            try:
                # Create base case
                bc = await ApiBaseCase.create(
                    project_id=session.project_id,
                    interface_id=interface_id,
                    name=base.get("name", ""),
                    steps=base.get("steps", []),
                    dependencies=base.get("dependencies"),
                    expected=base.get("expected", []),
                    status=ApiBaseCaseStatus.draft,
                    source=SourceType.ai,
                    generation_session_id=session.id,
                    created_by_id=session.created_by_id,
                )

                # Build main payload from pre_result.api_case (same as confirm flow)
                main_payload = dict(pre_result.api_case) if isinstance(pre_result.api_case, dict) else {}

                # Inject precondition IDs into main case payload
                if precondition_map:
                    main_payload["preconditions"] = []
                    dep_names = [
                        ApiCaseGenerationService._clean_dependency_name(str(d).strip())
                        for d in (base.get("dependencies") or [])
                    ]
                    main_payload["precondition_ids"] = [
                        precondition_map[n] for n in dep_names if n in precondition_map
                    ]

                tc = await ApiTestCase.create(
                    project_id=session.project_id,
                    interface_id=interface_id,
                    base_case_id=bc.id,
                    title=case_title,
                    case_kind=ApiCaseKind.main,
                    sort_order=idx,
                    case_payload=main_payload,
                    review_status=pre_result.review_status if isinstance(pre_result.review_status, ReviewStatus) else ReviewStatus.init,
                    exec_status=initial_exec_status,
                    environment_id=environment_id,
                    generation_session_id=session.id,
                    created_by_id=session.created_by_id,
                    updated_by_id=session.created_by_id,
                )
                created_case_ids.append(tc.id)
            except Exception as e:
                _log.error("[pipeline] 创建用例失败 '%s': %s", case_title, e)
                # 单个用例失败不影响后续用例

        return created_case_ids

    @classmethod
    async def _execute_cases(cls, case_ids: list[int], environment_id: int, user_id: int) -> dict:
        """Execute structured cases by ID and return results summary."""
        if not case_ids:
            return {"total": 0, "passed": 0, "failed": 0, "error": 0, "pass_rate": 0}

        from service.api_test.shared.runner_gateway import RunnerGateway
        from service.api_test.models import ApiTestCase
        from service.core.enums import ExecStatus, CaseRunStatus

        passed = 0
        failed = 0
        error = 0
        for case_id in case_ids:
            try:
                record = await RunnerGateway.run_case_debug(
                    case_id=case_id,
                    environment_id=environment_id,
                    triggered_by_id=user_id,
                )
                if record.status == CaseRunStatus.success:
                    passed += 1
                    await ApiTestCase.filter(id=case_id).update(exec_status=ExecStatus.success)
                elif record.status == CaseRunStatus.fail:
                    failed += 1
                    await ApiTestCase.filter(id=case_id).update(exec_status=ExecStatus.fail)
                else:
                    error += 1
                    await ApiTestCase.filter(id=case_id).update(exec_status=ExecStatus.error)
            except Exception:
                error += 1
                try:
                    await ApiTestCase.filter(id=case_id).update(exec_status=ExecStatus.error)
                except Exception:
                    pass

        total = passed + failed + error
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "error": error,
            "skipped": len(case_ids) - total,
            "pass_rate": passed / total if total > 0 else 0,
        }

    @classmethod
    async def _sync_debug_templates(cls, interfaces: list[dict]) -> None:
        """将预执行结果同步写入接口调试模板（ApiInterfaceDebugTemplate）。

        取每个接口最后一次非 error 状态的执行记录，从 request_info 中
        提取真实的请求参数，写入 debug template，使"接口调试"tab 有初始数据。
        """
        from service.test_execution.models import ApiCaseRunRecord
        from service.api_test.interface.models import ApiInterfaceDebugTemplate
        from service.core.enums import CaseRunStatus
        from urllib.parse import urlparse, parse_qs

        _log.info("[_sync_debug_templates] 开始同步调试模板，共 %d 个接口", len(interfaces))

        for iface in interfaces:
            interface_id = iface.get("interface_id")
            iface_summary = iface.get("summary", "")
            if not interface_id:
                _log.warning("[_sync_debug_templates] 接口缺少 interface_id，跳过: %s", iface_summary)
                continue

            _log.info("[_sync_debug_templates] 处理接口: id=%s, summary=%s", interface_id, iface_summary)

            # 取最后一条非 error 的执行记录（排除前置用例的记录）
            # 前置用例的记录结构是 {"_precondition_detail": ..., "log_data": ...}
            # 主用例的记录结构是 {"_debug_detail": {...}, ...}
            records = await ApiCaseRunRecord.filter(
                interface_id=interface_id,
                run_type="debug",
            ).exclude(
                status=CaseRunStatus.error,
            ).order_by("-created_at").limit(10)

            # 找到第一个包含 _debug_detail 的记录（即主用例记录）
            record = None
            for r in records:
                if r.api_requests_info and "_debug_detail" in r.api_requests_info:
                    record = r
                    break

            if not record:
                _log.warning("[_sync_debug_templates] 未找到主用例执行记录: interface_id=%s", interface_id)
                continue

            if not record.api_requests_info:
                _log.warning("[_sync_debug_templates] 执行记录缺少 api_requests_info: record_id=%s", record.id)
                continue

            _log.info("[_sync_debug_templates] 找到执行记录: record_id=%s, status=%s", record.id, record.status)

            debug_detail = record.api_requests_info.get("_debug_detail") or {}
            request_info = debug_detail.get("request_info") or {}

            # 添加详细日志，帮助诊断问题
            _log.info("[_sync_debug_templates] record_id=%s, debug_detail keys=%s, request_info keys=%s",
                     record.id, list(debug_detail.keys()), list(request_info.keys()) if request_info else "None")

            if not request_info:
                _log.warning("[_sync_debug_templates] 执行记录缺少 request_info: record_id=%s, api_requests_info keys=%s",
                           record.id, list(record.api_requests_info.keys()))
                continue

            # 从实际请求 URL 中提取 path_params
            actual_url = request_info.get("url") or ""
            iface_path = iface.get("path") or ""
            path_params = {}
            if actual_url and iface_path:
                try:
                    parsed = urlparse(actual_url)
                    actual_path = parsed.path
                    # 对比接口路径模板和实际路径，提取 path params
                    # e.g. /api/user/{id} vs /api/user/123
                    template_parts = iface_path.strip("/").split("/")
                    actual_parts = actual_path.strip("/").split("/")
                    if len(template_parts) == len(actual_parts):
                        for t, a in zip(template_parts, actual_parts):
                            if t.startswith("{") and t.endswith("}"):
                                param_name = t[1:-1]
                                path_params[param_name] = a
                except Exception:
                    pass

            # 检测 Content-Type，区分 form-urlencoded 和 json
            req_headers = request_info.get("headers") or {}
            content_type = (req_headers.get("Content-Type") or req_headers.get("content-type") or "").lower()
            raw_body = request_info.get("body")

            if "form-urlencoded" in content_type and isinstance(raw_body, str) and "=" in raw_body:
                # form 数据：解析为 urlencoded_rows
                from urllib.parse import parse_qs
                parsed = parse_qs(raw_body, keep_blank_values=True)
                body_type = "urlencoded"
                urlencoded_rows = [
                    {"name": k, "value": v[0] if v else "", "desc": ""}
                    for k, v in parsed.items()
                ]
                body_value = None
            else:
                body_type = "json"
                urlencoded_rows = []
                body_value = raw_body

            # 从第一个主用例读取断言
            from service.api_test.models import ApiTestCase as _ApiTestCase
            from service.core.enums import ApiCaseKind
            assertions = []
            try:
                main_case = await _ApiTestCase.filter(
                    interface_id=interface_id, case_kind=ApiCaseKind.main
                ).order_by("sort_order").first()
                if main_case and main_case.case_payload and isinstance(main_case.case_payload, dict):
                    assertions = main_case.case_payload.get("assertions") or []
            except Exception:
                pass

            # 转换断言格式：引擎格式 {type, field, expected} → 前端格式 {target, comparator, expected}
            # 确保调试模板在前 ApiTestWorkspaceView.populateFormFromPayload() 中正确显示
            frontend_assertions = []
            for a in (assertions or []):
                if isinstance(a, dict):
                    frontend_assertions.append({
                        "target": a.get("field") or a.get("target") or "",
                        "comparator": a.get("type") or a.get("comparator") or "eq",
                        "expected": a.get("expected") if "expected" in a else "",
                    })
                else:
                    frontend_assertions.append({"target": str(a), "comparator": "eq", "expected": ""})
            assertions = frontend_assertions

            payload = {
                "method": request_info.get("method") or iface.get("method") or "GET",
                "path": iface_path,
                "headers": req_headers,
                "query": request_info.get("params") or {},
                "path_params": path_params,
                "body": body_value,
                "body_type": body_type,
                "urlencoded_rows": urlencoded_rows,
                # 执行结果（4A 修复）
                "response_info": debug_detail.get("response_info"),
                "exec_status": record.status.value if record.status else None,
                "duration_ms": debug_detail.get("duration_ms"),
                # 断言（4B-2 修复）
                "assertions": assertions,
                # 断言执行结果（含 passed/actual，供响应面板断言 tab 显示）
                "assert_info": debug_detail.get("assert_info") or [],
            }

            try:
                tpl, created = await ApiInterfaceDebugTemplate.get_or_create(
                    interface_id=interface_id,
                )
                tpl.payload = payload
                await tpl.save()
                _log.info("[_sync_debug_templates] 调试模板保存成功: interface_id=%s, created=%s", interface_id, created)
            except Exception as e:
                _log.warning("[_sync_debug_templates] 保存失败: interface_id=%s, error=%s", interface_id, e)

        _log.info("[_sync_debug_templates] 同步完成")

    # ------------------------------------------------------------------
    # Progress helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _init_progress(mode: str, current_phase: int = 1) -> dict:
        if mode in ("from_doc", "from_prompt"):
            phases = [
                {"id": 1, "name": "生成测试接口", "status": "running"},
                {"id": 2, "name": "生成基础用例", "status": "pending"},
                {"id": 3, "name": "用例编辑确认", "status": "pending"},
                {"id": 4, "name": "生成结构化用例", "status": "pending"},
                {"id": 5, "name": "接口用例预执行", "status": "pending"},
            ]
        else:
            phases = [
                {"id": 1, "name": "生成基础用例", "status": "running"},
                {"id": 2, "name": "用例编辑确认", "status": "pending"},
                {"id": 3, "name": "生成结构化用例", "status": "pending"},
                {"id": 4, "name": "接口用例预执行", "status": "pending"},
            ]
        return {"current_phase": current_phase, "phases": phases}

    @staticmethod
    def _update_progress(progress: dict, phase: int, status: str) -> dict:
        for p in progress.get("phases", []):
            if p["id"] == phase:
                p["status"] = status
            elif p["status"] == "pending" and status == "done":
                # Mark next pending phase as running
                if p["id"] == phase + 1:
                    p["status"] = "running"
        progress["current_phase"] = phase
        return progress

    @staticmethod
    def _finalize_progress(progress: dict) -> dict:
        for p in progress.get("phases", []):
            if p["status"] in ("running", "pending"):
                p["status"] = "done"
        return progress

    @staticmethod
    def _build_summary(interfaces: list[dict]) -> dict:
        total_cases = 0
        total_passed = 0
        total_total = 0
        per_interface = []
        has_errors = False

        for iface in interfaces:
            sc = iface.get("structured_count", len(iface.get("structured_cases", [])))
            total_cases += sc
            er = iface.get("exec_results", {})
            structure_error = iface.get("structure_error")
            if structure_error:
                has_errors = True
            total_passed += er.get("passed", 0)
            total_total += er.get("total", 0)
            per_interface.append({
                "interface_id": iface.get("interface_id"),
                "summary": iface.get("summary", ""),
                "method": iface.get("method", ""),
                "path": iface.get("path", ""),
                "base_case_count": len(iface.get("base_cases", [])),
                "structured_case_count": sc,
                "exec_results": er,
                "structure_error": structure_error,
            })

        return {
            "total_interfaces": len(interfaces),
            "total_cases": total_cases,
            "overall_pass_rate": total_passed / total_total if total_total > 0 else 0,
            "has_errors": has_errors,
            "per_interface": per_interface,
        }
