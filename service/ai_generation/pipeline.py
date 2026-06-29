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

from service.ai_generation.models import AIGenerationSession
from service.core.enums import SessionStatus

_log = logging.getLogger("agent_pipeline")


def _sse(event: str, data: Any) -> str:
    import json as _json
    payload = _json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else _json.dumps(str(data), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


class ApiAgentPipeline:
    """Multi-interface deterministic pipeline."""

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
        """SSE Stream 1: Phase 1 -> 2 -> 3."""
        try:
            payload = dict(session.output_payload or {})
            payload["mode"] = mode
            payload["user_prompt"] = user_prompt or ""
            payload["interfaces"] = []
            payload["pipeline_progress"] = cls._init_progress(mode, current_phase=1)

            session.status = SessionStatus.running
            session.output_payload = payload
            await session.save(update_fields=["status", "output_payload"])

            # -- Phase 1: Create interfaces (Mode 1 only) --
            if mode == "from_doc" and api_doc_text:
                yield _sse("stage", {
                    "name": "create_interfaces",
                    "status": "running",
                    "text": "正在解析接口文档...",
                })
                interfaces_data = await cls._phase1_create_interfaces(
                    session, api_doc_text
                )
                payload["interfaces"] = interfaces_data
                yield _sse("stage", {
                    "name": "create_interfaces",
                    "status": "done",
                    "text": f"解析完成，共发现 {len(interfaces_data)} 个接口",
                })
                yield _sse("pipeline_progress", cls._update_progress(
                    payload["pipeline_progress"], phase=1, status="done"
                ))
            elif mode == "from_interfaces" and interface_ids:
                # Load existing interfaces
                interfaces_data = await cls._load_existing_interfaces(interface_ids, session.project_id)
                payload["interfaces"] = interfaces_data
                # Skip phase 1
                yield _sse("pipeline_progress", cls._update_progress(
                    payload["pipeline_progress"], phase=1, status="done"
                ))

            # -- Phase 2/1: Generate base cases per interface --
            yield _sse("stage", {
                "name": "generate_base_cases",
                "status": "running",
                "text": "正在为各接口生成基础用例...",
            })

            for i, iface in enumerate(payload["interfaces"]):
                yield _sse("custom", f"正在为「{iface.get('summary', '')}」生成基础用例...")
                try:
                    base_cases = await cls._generate_base_cases_for_interface(
                        iface, user_prompt
                    )
                    iface["base_cases"] = base_cases
                    iface["selected_indexes"] = list(range(len(base_cases)))
                    yield _sse("custom", f"✅ 「{iface.get('summary', '')}」生成 {len(base_cases)} 条基础用例")
                    yield _sse("interface_progress", {
                        "interface_index": i,
                        "phase": "base_cases_done",
                        "case_count": len(base_cases),
                    })
                except Exception as e:
                    _log.error("基础用例生成失败 [%s]: %s", iface.get("summary"), e, exc_info=True)
                    iface["base_cases"] = []
                    iface["selected_indexes"] = []
                    iface["error"] = str(e)
                    yield _sse("custom", f"❌ 「{iface.get('summary', '')}」生成失败: {str(e)[:100]}")

            yield _sse("stage", {
                "name": "generate_base_cases",
                "status": "done",
                "text": "基础用例生成完毕",
            })
            yield _sse("pipeline_progress", cls._update_progress(
                payload["pipeline_progress"], phase=2, status="done"
            ))

            # -- Phase 3/2: Present cards --
            # Save payload to DB
            session.output_payload = payload
            session.status = SessionStatus.success
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["output_payload", "status", "finished_at"])

            yield _sse("stage", {
                "name": "edit_base_cases",
                "status": "running",
                "text": "请检查并编辑基础用例",
            })
            yield _sse("pipeline_progress", cls._update_progress(
                payload["pipeline_progress"], phase=3, status="running"
            ))
            yield _sse("payload_updated", {})
            yield _sse("done", {})

        except Exception as e:
            _log.error("Pipeline phase 1-3 failed: %s", e, exc_info=True)
            session.status = SessionStatus.failed
            session.error_message = str(e)
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["status", "error_message", "finished_at"])
            yield _sse("error", {"message": str(e)})
            yield _sse("done", {})

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
        """SSE Stream 2: Phase 4 -> 5 + summary."""
        try:
            payload = dict(session.output_payload or {})
            interfaces = payload.get("interfaces", [])

            session.status = SessionStatus.running
            await session.save(update_fields=["status"])

            # -- Phase 4/3: Generate structured cases --
            yield _sse("stage", {
                "name": "structure_cases",
                "status": "running",
                "text": "正在生成结构化测试用例...",
            })

            from service.api_test.case.generation_service import ApiCaseGenerationService

            for i, iface in enumerate(interfaces):
                selected_indexes = iface.get("selected_indexes", [])
                base_cases = iface.get("base_cases", [])
                if not selected_indexes or not base_cases:
                    continue

                yield _sse("custom", f"正在为「{iface.get('summary', '')}」生成结构化用例...")

                selected_items = [
                    (idx, base_cases[idx])
                    for idx in selected_indexes
                    if idx < len(base_cases) and isinstance(base_cases[idx], dict)
                ]

                if not selected_items:
                    continue

                try:
                    # Build interface doc for structuring
                    api_doc = iface.get("api_doc", "")
                    if isinstance(api_doc, dict):
                        api_doc = json.dumps(api_doc, ensure_ascii=False)

                    # Load precondition docs
                    precoditions_api_doc = await cls._load_preconditions(
                        iface, session.project_id
                    )

                    # Run structuring (skip_execution=True)
                    pre_run_results = await ApiCaseGenerationService._pre_run_selected_base_cases(
                        selected_items=selected_items,
                        api_doc=api_doc,
                        precoditions_api_doc=precoditions_api_doc,
                        environment_id=environment_id or 0,
                        project_id=session.project_id,
                        test_env_data=None,
                        skip_execution=True,
                    )

                    iface["structured_cases"] = [r.api_case for r in pre_run_results if r.api_case]
                    iface["structured_count"] = len(iface["structured_cases"])
                    yield _sse("custom", f"✅ 「{iface.get('summary', '')}」结构化完成: {len(iface['structured_cases'])} 条")

                    # Save to DB (create ApiBaseCase + ApiTestCase records)
                    interface_id = iface.get("interface_id")
                    if interface_id:
                        await cls._save_cases_to_db(
                            session, iface, selected_items, pre_run_results, interface_id
                        )

                except Exception as e:
                    _log.error("结构化失败 [%s]: %s", iface.get("summary"), e, exc_info=True)
                    iface["structured_cases"] = []
                    iface["structure_error"] = str(e)
                    yield _sse("custom", f"❌ 「{iface.get('summary', '')}」结构化失败: {str(e)[:100]}")

                yield _sse("interface_progress", {
                    "interface_index": i,
                    "phase": "structured_done",
                    "structured_count": iface.get("structured_count", 0),
                })

            yield _sse("stage", {
                "name": "structure_cases",
                "status": "done",
                "text": "结构化用例生成完毕",
            })

            # -- Phase 5/4: Pre-execute --
            if environment_id:
                yield _sse("stage", {
                    "name": "pre_run",
                    "status": "running",
                    "text": "正在预执行测试用例...",
                })

                for i, iface in enumerate(interfaces):
                    structured = iface.get("structured_cases", [])
                    if not structured:
                        continue
                    yield _sse("custom", f"正在预执行「{iface.get('summary', '')}」的用例...")
                    try:
                        exec_results = await cls._execute_cases(
                            iface, environment_id, session.project_id
                        )
                        iface["exec_results"] = exec_results
                        yield _sse("custom", f"✅ 「{iface.get('summary', '')}」预执行完成: "
                                  f"通过率 {exec_results.get('pass_rate', 0):.0%}")
                    except Exception as e:
                        _log.error("预执行失败 [%s]: %s", iface.get("summary"), e, exc_info=True)
                        iface["exec_results"] = {"total": len(structured), "passed": 0, "failed": 0, "pass_rate": 0, "error": str(e)}
                        yield _sse("custom", f"❌ 「{iface.get('summary', '')}」预执行失败")

                    yield _sse("interface_progress", {
                        "interface_index": i,
                        "phase": "exec_done",
                        "exec_results": iface.get("exec_results", {}),
                    })

                yield _sse("stage", {
                    "name": "pre_run",
                    "status": "done",
                    "text": "预执行完毕",
                })

            # -- Summary --
            summary = cls._build_summary(interfaces)
            payload["summary"] = summary
            payload["pipeline_progress"] = cls._finalize_progress(payload.get("pipeline_progress", {}))

            session.output_payload = payload
            session.status = SessionStatus.success
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["output_payload", "status", "finished_at"])

            yield _sse("summary", summary)
            yield _sse("payload_updated", {})
            yield _sse("done", {})

        except Exception as e:
            _log.error("Pipeline phase 4-5 failed: %s", e, exc_info=True)
            session.status = SessionStatus.failed
            session.error_message = str(e)
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["status", "error_message", "finished_at"])
            yield _sse("error", {"message": str(e)})
            yield _sse("done", {})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    async def _phase1_create_interfaces(
        cls, session: AIGenerationSession, api_doc_text: str
    ) -> list[dict]:
        """Parse API doc and create interfaces in DB. Returns interface data list."""
        from utils.parser.api_document_ai_parser import APIDocumentParser

        parsed = APIDocumentParser().api_parser(api_doc_text)
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

            # Create new interface
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
        cls, iface_data: dict, user_prompt: str | None
    ) -> list[dict]:
        """Run base case generation workflow for a single interface."""
        from workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow

        api_doc = iface_data.get("api_doc", "")
        if isinstance(api_doc, dict):
            api_doc = json.dumps(api_doc, ensure_ascii=False)

        workflow = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
        state = workflow.invoke({
            "api_doc": api_doc,
            "precoditions": [],
            "user_prompt": user_prompt,
        })
        return state.get("api_cases") or []

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
            max_order = await ApiInterfaceCatalog.filter(
                project_id=project_id, parent_id=None
            ).annotate(max_sort=Max("sort_order")).values("max_sort").first()
            next_order = (max_order.get("max_sort") or 0) + 1 if max_order else 0

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
    async def _save_cases_to_db(cls, session, iface_data, selected_items, pre_run_results, interface_id):
        """Save base cases and test cases to DB for one interface."""
        from service.api_test.case.models import ApiBaseCase, ApiTestCase

        base_cases = iface_data.get("base_cases", [])
        structured = iface_data.get("structured_cases", [])

        for idx, (orig_idx, base) in enumerate(selected_items):
            # Create base case
            bc = await ApiBaseCase.create(
                interface_id=interface_id,
                name=base.get("name", ""),
                steps=base.get("steps", []),
                dependencies=base.get("dependencies", []),
                expected=base.get("expected", []),
                source="ai",
                ai_session_id=session.id,
            )
            # Create test case if structured version exists
            if idx < len(structured) and structured[idx]:
                await ApiTestCase.create(
                    interface_id=interface_id,
                    base_case_id=bc.id,
                    title=base.get("name", ""),
                    case_kind="main",
                    case_payload=structured[idx],
                    review_status="pending",
                    created_by_id=session.created_by_id,
                )

    @classmethod
    async def _execute_cases(cls, iface_data, environment_id, project_id) -> dict:
        """Execute structured cases and return results summary."""
        structured = iface_data.get("structured_cases", [])
        if not structured:
            return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0}

        from service.test_execution.run.runner_gateway import RunnerGateway

        passed = 0
        failed = 0
        for case_payload in structured:
            try:
                result = await RunnerGateway.run_case_debug(
                    case_payload=case_payload,
                    environment_id=environment_id,
                    project_id=project_id,
                )
                if result and result.get("status") == "pass":
                    passed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        total = passed + failed
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": len(structured) - total,
            "pass_rate": passed / total if total > 0 else 0,
        }

    # ------------------------------------------------------------------
    # Progress helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _init_progress(mode: str, current_phase: int = 1) -> dict:
        if mode == "from_doc":
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

        for iface in interfaces:
            sc = iface.get("structured_count", len(iface.get("structured_cases", [])))
            total_cases += sc
            er = iface.get("exec_results", {})
            total_passed += er.get("passed", 0)
            total_total += er.get("total", 0)
            per_interface.append({
                "summary": iface.get("summary", ""),
                "method": iface.get("method", ""),
                "path": iface.get("path", ""),
                "base_case_count": len(iface.get("base_cases", [])),
                "structured_case_count": sc,
                "exec_results": er,
            })

        return {
            "total_interfaces": len(interfaces),
            "total_cases": total_cases,
            "overall_pass_rate": total_passed / total_total if total_total > 0 else 0,
            "per_interface": per_interface,
        }
