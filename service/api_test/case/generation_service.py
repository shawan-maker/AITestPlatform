import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from tortoise.transactions import in_transaction

from service.ai_generation.common import (
    LLM_NOT_CONFIGURED_MSG,
    api_test_gen_use_mock,
    build_default_additional_info,
    compute_prompt_hash,
    is_llm_configured,
)
from service.ai_generation.models import AIGenerationSession
from service.ai_generation.session_lifecycle import session_to_out
from service.ai_generation.session_schemas import AIGenerationSessionOut
from service.api_test.case.schemas import (
    ApiConfirmRequest,
    ApiConfirmResult,
    ApiSessionPreviewUpdateRequest,
    BaseCasePreviewItem,
    GenerateConfirmRequest,
    GenerateConfirmResult,
    GeneratePreviewRequest,
    GeneratePreviewResult,
    PreviewFromDocRequest,
)
from service.api_test.dependency.resolver_service import DependencyResolverService
from service.api_test.interface.interface_service import InterfaceService
from service.api_test.interface.models import ApiInterface
from service.api_test.interface.schemas import InterfaceCreateRequest
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
    SourceChannel,
    SourceType,
)
from service.core.exceptions import AppException
from service.test_environment.models import TestEnvironment
from service.user.models import User


@dataclass
class _PreRunResult:
    index: int
    api_case: dict
    review_status: ReviewStatus
    error: str | None = None


class ApiCaseGenerationService:
    @classmethod
    async def _get_api_session_or_404(cls, session_id: int) -> AIGenerationSession:
        session = await AIGenerationSession.get_or_none(id=session_id)
        if session is None:
            raise AppException("生成会话不存在", 404)
        if session.gen_type != GenType.api_base:
            raise AppException("非接口用例生成会话", 400)
        return session

    @classmethod
    def _to_session_out(cls, session: AIGenerationSession) -> AIGenerationSessionOut:
        return session_to_out(session)

    @classmethod
    async def preview(
        cls,
        user: User,
        interface_id: int,
        data: GeneratePreviewRequest,
    ) -> GeneratePreviewResult:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_viewer(iface.project_id, user)
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
            prompt_hash=compute_prompt_hash(api_doc, data.user_prompt),
            source_channel=SourceChannel.interface_detail,
            created_by_id=user.id,
        )

        try:
            if api_test_gen_use_mock():
                base_cases = cls._mock_base_cases(iface.summary or iface.path)
            elif not is_llm_configured():
                session.status = SessionStatus.failed
                session.error_message = LLM_NOT_CONFIGURED_MSG
                session.finished_at = datetime.now(timezone.utc)
                await session.save(
                    update_fields=["status", "error_message", "finished_at"]
                )
                raise AppException(LLM_NOT_CONFIGURED_MSG, 503)
            else:
                base_cases = await asyncio.to_thread(
                    cls._invoke_basecase_workflow,
                    api_doc,
                    precoditions,
                    data.user_prompt,
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
    async def preview_from_doc(
        cls,
        user: User,
        data: PreviewFromDocRequest,
    ) -> GeneratePreviewResult:
        await ensure_api_viewer(data.project_id, user)
        await InterfaceService._validate_module(data.project_id, data.module_id)
        api_doc_text = data.api_doc_text.strip()
        if not api_doc_text:
            raise AppException("接口文档不能为空", 400)

        session = await AIGenerationSession.create(
            project_id=data.project_id,
            module_id=data.module_id,
            gen_type=GenType.api_base,
            input_ref_type=InputRefType.api_doc,
            input_ref_id=None,
            status=SessionStatus.running,
            user_prompt=data.user_prompt,
            prompt_hash=compute_prompt_hash(api_doc_text, data.user_prompt),
            source_channel=SourceChannel.interface_detail,
            created_by_id=user.id,
        )

        precoditions: list[str] = []
        try:
            if api_test_gen_use_mock():
                base_cases = cls._mock_base_cases("api-doc")
            elif not is_llm_configured():
                session.status = SessionStatus.failed
                session.error_message = LLM_NOT_CONFIGURED_MSG
                session.finished_at = datetime.now(timezone.utc)
                await session.save(
                    update_fields=["status", "error_message", "finished_at"]
                )
                raise AppException(LLM_NOT_CONFIGURED_MSG, 503)
            else:
                base_cases = await asyncio.to_thread(
                    cls._invoke_basecase_workflow,
                    api_doc_text,
                    precoditions,
                    data.user_prompt,
                )
            session.status = SessionStatus.success
            session.output_payload = {
                "base_cases": base_cases,
                "api_doc": api_doc_text,
                "precoditions_api_doc": [],
                "environment_id": None,
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
    async def get_session(cls, user: User, session_id: int) -> AIGenerationSessionOut:
        session = await cls._get_api_session_or_404(session_id)
        await ensure_api_viewer(session.project_id, user)
        return cls._to_session_out(session)

    @classmethod
    async def update_preview(
        cls,
        user: User,
        session_id: int,
        data: ApiSessionPreviewUpdateRequest,
    ) -> AIGenerationSessionOut:
        session = await cls._get_api_session_or_404(session_id)
        await ensure_api_viewer(session.project_id, user)
        session.output_payload = data.output_payload
        await session.save(update_fields=["output_payload"])
        return cls._to_session_out(session)

    @classmethod
    async def confirm(
        cls,
        user: User,
        interface_id: int,
        data: GenerateConfirmRequest,
    ) -> GenerateConfirmResult:
        result = await cls.confirm_session(
            user,
            ApiConfirmRequest(
                session_id=data.session_id,
                selected_indexes=data.selected_indexes,
                environment_id=data.environment_id,
                interface_id=interface_id,
            ),
        )
        return GenerateConfirmResult(
            created_base_case_ids=result.created_base_case_ids,
            created_case_ids=result.created_case_ids,
            run_errors=result.run_errors,
        )

    @classmethod
    async def confirm_session(
        cls,
        user: User,
        data: ApiConfirmRequest,
    ) -> ApiConfirmResult:
        session = await cls._get_api_session_or_404(data.session_id)
        await ensure_api_editor(session.project_id, user)
        if session.status != SessionStatus.success or not session.output_payload:
            raise AppException("生成会话未完成", 400)

        env = await TestEnvironment.get_or_none(
            id=data.environment_id, project_id=session.project_id
        )
        if env is None:
            raise AppException("测试环境不存在", 404)

        created_interface_id: int | None = None
        if session.input_ref_type == InputRefType.interface:
            interface_id = data.interface_id or session.input_ref_id
            if interface_id is None:
                raise AppException("interface_id 必填", 400)
            iface = await InterfaceService._get_current_or_404(interface_id)
            if session.input_ref_id != iface.id:
                raise AppException("生成会话不存在", 404)
            resolved = await DependencyResolverService.resolve(iface.id)
            precoditions_api_doc = resolved.precoditions_api_doc
        elif session.input_ref_type == InputRefType.api_doc:
            if data.catalog_id is None:
                raise AppException("catalog_id 必填", 400)
            module_id = session.module_id
            iface = await cls._create_interface_from_doc(
                user,
                project_id=session.project_id,
                catalog_id=data.catalog_id,
                api_doc_text=session.output_payload.get("api_doc") or "",
                module_id=module_id,
            )
            created_interface_id = iface.id
            precoditions_api_doc = []
        else:
            raise AppException("不支持的生成会话类型", 400)

        base_cases = session.output_payload.get("base_cases") or []
        api_doc = session.output_payload.get("api_doc") or interface_to_doc_json(iface)

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

        return ApiConfirmResult(
            created_base_case_ids=created_base_ids,
            created_case_ids=created_case_ids,
            run_errors=run_errors,
            created_interface_id=created_interface_id,
        )

    @classmethod
    async def _create_interface_from_doc(
        cls,
        user: User,
        *,
        project_id: int,
        catalog_id: int,
        api_doc_text: str,
        module_id: int | None,
    ) -> ApiInterface:
        parsed = cls._parse_api_doc(api_doc_text)
        method = str(parsed.get("method") or "").upper()
        path = str(parsed.get("path") or "")
        if not method or not path:
            raise AppException("无法从文档解析 method 与 path", 400)

        create_data = InterfaceCreateRequest(
            project_id=project_id,
            catalog_id=catalog_id,
            module_id=module_id,
            method=method,
            path=path,
            summary=parsed.get("summary"),
            parameters=parsed.get("parameters"),
            request_body=parsed.get("requestBody"),
            responses=parsed.get("responses"),
        )
        out = await InterfaceService.create(user, create_data)
        return await InterfaceService._get_current_or_404(out.id)

    @staticmethod
    def _parse_api_doc(api_doc_text: str) -> dict:
        if api_test_gen_use_mock():
            method_match = re.search(r"Method:\s*(\w+)", api_doc_text, re.IGNORECASE)
            path_match = re.search(r"Path:\s*(\S+)", api_doc_text, re.IGNORECASE)
            return {
                "method": (method_match.group(1) if method_match else "GET").upper(),
                "path": path_match.group(1) if path_match else "/mock/from-doc",
                "summary": "mock from doc",
                "parameters": {"header": [], "path": [], "query": []},
                "requestBody": None,
                "responses": [],
            }

        from utils.parser.api_document_ai_parser import APIDocumentParser

        parsed = APIDocumentParser().api_parser(api_doc_text)
        if not parsed:
            raise AppException("无法解析接口文档", 400)
        item = parsed[0] if isinstance(parsed, list) else parsed
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        elif not isinstance(item, dict):
            item = dict(item)
        return item

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
    def _invoke_basecase_workflow(
        api_doc: str,
        precoditions: list[str],
        user_prompt: str | None = None,
    ) -> list[dict]:
        from workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow

        graph = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
        config = {"configurable": {"thread_id": "api-test-gen"}}
        result = graph.invoke(
            {
                "api_doc": api_doc,
                "precoditions": precoditions,
                "user_prompt": user_prompt,
            },
            config=config,
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
        if api_test_gen_use_mock():
            return [
                _PreRunResult(
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

        from workflow.api_case_main_workflow import concurrent_pre_run_base_cases

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
            additional_info=build_default_additional_info(),
        )
