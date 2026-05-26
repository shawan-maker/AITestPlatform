import asyncio
import json
import os
from datetime import datetime, timezone

from tortoise.transactions import in_transaction

from service.ai_generation.models import AIGenerationSession
from service.api_test.case.schemas import (
    BaseCasePreviewItem,
    GenerateConfirmRequest,
    GenerateConfirmResult,
    GeneratePreviewRequest,
    GeneratePreviewResult,
)
from service.api_test.dependency.resolver_service import DependencyResolverService
from service.api_test.interface.interface_service import InterfaceService
from service.api_test.models import ApiBaseCase, ApiTestCase
from service.api_test.permissions import ensure_api_editor, ensure_api_viewer
from service.api_test.shared.interface_doc import interface_to_doc_json
from service.core.enums import (
    ApiBaseCaseStatus,
    ApiCaseKind,
    ExecStatus,
    GenType,
    InputRefType,
    ReviewStatus,
    SessionStatus,
    SourceType,
)
from service.core.exceptions import AppException
from service.test_environment.models import TestEnvironment
from service.user.models import User


class GenerationService:
    @classmethod
    async def preview(
        cls,
        user: User,
        interface_id: int,
        data: GeneratePreviewRequest,
    ) -> GeneratePreviewResult:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        resolved = await DependencyResolverService.resolve(iface.id)
        api_doc = interface_to_doc_json(iface)
        precoditions = resolved.precoditions_summaries

        session = await AIGenerationSession.create(
            project_id=iface.project_id,
            module_id=iface.module_id,
            gen_type=GenType.api_base,
            input_ref_type=InputRefType.interface,
            input_ref_id=iface.id,
            status=SessionStatus.running,
            user_prompt=data.user_prompt,
            created_by_id=user.id,
        )

        try:
            if os.getenv("API_TEST_GEN_MOCK") == "1" or not os.getenv("LLM_BINDING_API_KEY"):
                base_cases = cls._mock_base_cases(iface.summary or iface.path)
            else:
                base_cases = await asyncio.to_thread(
                    cls._invoke_basecase_workflow, api_doc, precoditions
                )
            session.status = SessionStatus.success
            session.output_payload = {
                "base_cases": base_cases,
                "api_doc": api_doc,
                "precoditions_api_doc": resolved.precoditions_api_doc,
                "environment_id": data.environment_id,
            }
            session.finished_at = datetime.now(timezone.utc)
            await session.save(
                update_fields=["status", "output_payload", "finished_at"]
            )
        except Exception as exc:
            session.status = SessionStatus.failed
            session.error_message = str(exc) or repr(exc)
            session.finished_at = datetime.now(timezone.utc)
            await session.save(
                update_fields=["status", "error_message", "finished_at"]
            )
            raise AppException(f"生成预览失败: {session.error_message}", 500)

        items = [
            BaseCasePreviewItem(
                index=i,
                name=str(c.get("name") or f"用例-{i + 1}"),
                steps=list(c.get("steps") or []),
                dependencies=list(c.get("dependencies") or []),
                expected=list(c.get("expected") or []),
            )
            for i, c in enumerate(base_cases)
        ]
        return GeneratePreviewResult(session_id=session.id, base_cases=items)

    @classmethod
    async def confirm(
        cls,
        user: User,
        interface_id: int,
        data: GenerateConfirmRequest,
    ) -> GenerateConfirmResult:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        session = await AIGenerationSession.get_or_none(id=data.session_id)
        if session is None or session.input_ref_id != iface.id:
            raise AppException("生成会话不存在", 404)
        if session.status != SessionStatus.success or not session.output_payload:
            raise AppException("生成会话未完成", 400)

        env = await TestEnvironment.get_or_none(
            id=data.environment_id, project_id=iface.project_id
        )
        if env is None:
            raise AppException("测试环境不存在", 404)

        base_cases = session.output_payload.get("base_cases") or []
        api_doc = session.output_payload.get("api_doc") or interface_to_doc_json(iface)
        resolved = await DependencyResolverService.resolve(iface.id)
        precoditions_api_doc = resolved.precoditions_api_doc

        selected_items: list[tuple[int, dict]] = []
        for idx in data.selected_indexes:
            if idx < 0 or idx >= len(base_cases):
                raise AppException(f"无效的 selected_index: {idx}", 400)
            base = base_cases[idx]
            if not isinstance(base, dict):
                raise AppException("基础用例格式错误", 400)
            selected_items.append((idx, base))

        pre_run_results = await cls._pre_run_selected_base_cases(
            selected_items=selected_items,
            api_doc=api_doc,
            precoditions_api_doc=precoditions_api_doc,
            environment_id=data.environment_id,
            project_id=iface.project_id,
        )

        created_base_ids: list[int] = []
        created_case_ids: list[int] = []
        run_errors: list[str] = []

        async with in_transaction():
            sort_base = await cls._next_case_sort_order(iface.id, ApiCaseKind.main)
            for order, pre_result in enumerate(pre_run_results):
                idx = pre_result.index
                base = base_cases[idx]
                if pre_result.error:
                    run_errors.append(pre_result.error)

                base_row = await ApiBaseCase.create(
                    project_id=iface.project_id,
                    interface_id=iface.id,
                    name=str(base.get("name") or f"基础用例-{idx}"),
                    steps=base.get("steps") or [],
                    dependencies=base.get("dependencies"),
                    expected=base.get("expected") or [],
                    status=ApiBaseCaseStatus.draft,
                    source=SourceType.ai,
                    generation_session_id=session.id,
                    created_by_id=user.id,
                )
                created_base_ids.append(base_row.id)

                case_row = await ApiTestCase.create(
                    project_id=iface.project_id,
                    module_id=iface.module_id,
                    base_case_id=base_row.id,
                    interface_id=iface.id,
                    title=str(pre_result.api_case.get("title") or base_row.name),
                    case_kind=ApiCaseKind.main,
                    sort_order=sort_base + order,
                    case_payload=pre_result.api_case,
                    review_status=pre_result.review_status,
                    exec_status=ExecStatus.ready
                    if pre_result.review_status == ReviewStatus.success
                    else ExecStatus.pending,
                    environment_id=data.environment_id,
                    generation_session_id=session.id,
                    created_by_id=user.id,
                    updated_by_id=user.id,
                )
                created_case_ids.append(case_row.id)

        return GenerateConfirmResult(
            created_base_case_ids=created_base_ids,
            created_case_ids=created_case_ids,
            run_errors=run_errors,
        )

    @staticmethod
    async def _next_case_sort_order(interface_id: int, case_kind: ApiCaseKind) -> int:
        last = (
            await ApiTestCase.filter(interface_id=interface_id, case_kind=case_kind)
            .order_by("-sort_order")
            .first()
        )
        return (last.sort_order + 1) if last else 0

    @staticmethod
    def _mock_base_cases(summary: str) -> list[dict]:
        return [
            {
                "name": f"{summary}-正常流程",
                "steps": ["构造合法请求", "发送请求", "校验响应"],
                "dependencies": [],
                "expected": ["HTTP 200", "业务成功"],
            },
            {
                "name": f"{summary}-异常参数",
                "steps": ["构造非法参数", "发送请求", "校验错误响应"],
                "dependencies": [],
                "expected": ["返回参数错误提示"],
            },
        ]

    @staticmethod
    def _invoke_basecase_workflow(api_doc: str, precoditions: list[str]) -> list[dict]:
        from workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow

        graph = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
        config = {"configurable": {"thread_id": "api-test-gen"}}
        result = graph.invoke(
            {"api_doc": api_doc, "precoditions": precoditions},
            config=config,
            context={"project_name": "api_test", "module_id": "0"},
        )
        cases = result.get("api_cases") or []
        if isinstance(cases, str):
            cases = json.loads(cases)
        return cases if isinstance(cases, list) else []

    @classmethod
    async def _pre_run_selected_base_cases(
        cls,
        *,
        selected_items: list[tuple[int, dict]],
        api_doc: str,
        precoditions_api_doc: list,
        environment_id: int,
        project_id: int,
    ):
        from workflow.api_case_main_workflow import (
            BaseCasePreRunResult,
            concurrent_pre_run_base_cases,
        )

        if os.getenv("API_TEST_GEN_MOCK") == "1" or not os.getenv("LLM_BINDING_API_KEY"):
            return [
                BaseCasePreRunResult(
                    index=idx,
                    api_case={
                        "title": base.get("name"),
                        "method": "GET",
                        "path": "/mock",
                        "headers": {},
                        "query": {},
                        "body": None,
                        "assertions": base.get("expected") or [],
                    },
                    review_status=ReviewStatus.success,
                )
                for idx, base in selected_items
            ]

        indices = [idx for idx, _ in selected_items]
        base_cases = [base for _, base in selected_items]
        return await asyncio.to_thread(
            concurrent_pre_run_base_cases,
            base_cases,
            indices=indices,
            api_doc=api_doc,
            precoditions_api_doc=precoditions_api_doc,
            environment_id=environment_id,
            project_id=project_id,
        )
