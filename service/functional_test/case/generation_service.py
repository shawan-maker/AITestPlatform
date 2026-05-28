import asyncio
import os
from datetime import datetime, timezone

from tortoise.transactions import in_transaction

from service.ai_generation.common import (
    LLM_NOT_CONFIGURED_MSG,
    compute_prompt_hash,
    functional_gen_use_mock,
    is_llm_configured,
    load_knowledge_requirement_text,
)
from service.ai_generation.models import AIGenerationSession
from service.core.enums import (
    FunctionalCaseType,
    FunctionalExecResult,
    GenType,
    InputRefType,
    SessionStatus,
    SourceType,
)
from service.core.exceptions import AppException
from service.functional_test.case.catalog_service import CatalogService
from service.functional_test.case.case_service import CaseService
from service.functional_test.case.models import FunctionalCase, FunctionalTestPoint
from service.functional_test.permissions import ensure_case_editor, ensure_case_viewer
from service.ai_generation.session_lifecycle import session_to_out
from service.ai_generation.session_schemas import AIGenerationSessionOut
from service.functional_test.case.schemas import (
    GenerationPreviewUpdateRequest,
    GenerationSaveRequest,
    GenerationSaveResult,
    GenerationSessionCreateRequest,
)
from service.functional_test.requirement.models import RequirementDoc
from service.project.models import ProjectModule
from service.user.models import User

_PRIORITY_MAP = {"P0": 1, "P1": 2, "P2": 3, "P3": 4, "0": 1, "1": 2, "2": 3, "3": 4}


def _parse_priority(value) -> int:
    if isinstance(value, int):
        return max(1, min(4, value))
    if value is None:
        return 3
    text = str(value).strip().upper()
    if text in _PRIORITY_MAP:
        return _PRIORITY_MAP[text]
    try:
        num = int(text)
        return max(1, min(4, num))
    except ValueError:
        return 3


class FunctionalCaseGenerationService:
    @classmethod
    async def _get_session_or_404(cls, session_id: int) -> AIGenerationSession:
        session = await AIGenerationSession.get_or_none(id=session_id)
        if session is None:
            raise AppException("生成会话不存在", 404)
        if session.gen_type != GenType.functional:
            raise AppException("非功能用例生成会话", 400)
        return session

    @classmethod
    async def _resolve_requirement_text(
        cls,
        requirement_id: int | None,
        requirement_text: str | None,
    ) -> str:
        if requirement_text and requirement_text.strip():
            return requirement_text.strip()
        if requirement_id is None:
            raise AppException("requirement_id 或 requirement_text 至少提供一个", 400)
        doc = await RequirementDoc.get_or_none(id=requirement_id)
        if doc is None:
            raise AppException("需求不存在", 404)
        if doc.description and doc.description.strip():
            return doc.description.strip()
        return doc.title

    @classmethod
    async def _validate_create_input(cls, data: GenerationSessionCreateRequest) -> None:
        has_req_id = data.requirement_id is not None
        has_req_text = bool(data.requirement_text and data.requirement_text.strip())
        has_knowledge = data.knowledge_document_id is not None
        if not (has_req_id or has_req_text or has_knowledge):
            raise AppException(
                "requirement_id、requirement_text 或 knowledge_document_id 至少提供一个",
                400,
            )
        if has_req_text and has_knowledge:
            raise AppException("requirement_text 与 knowledge_document_id 不能同时提供", 400)
        if has_req_id and has_knowledge:
            raise AppException("requirement_id 与 knowledge_document_id 不能同时提供", 400)

    @classmethod
    async def _resolve_session_requirement_text(
        cls,
        data: GenerationSessionCreateRequest,
    ) -> tuple[str, int | None, InputRefType | None, int | None]:
        if data.knowledge_document_id is not None:
            text = await load_knowledge_requirement_text(
                data.knowledge_document_id, data.project_id
            )
            return text, data.knowledge_document_id, None, None
        text = await cls._resolve_requirement_text(data.requirement_id, data.requirement_text)
        input_ref_type = InputRefType.requirement if data.requirement_id else None
        return text, None, input_ref_type, data.requirement_id

    @classmethod
    async def _to_out(cls, session: AIGenerationSession) -> AIGenerationSessionOut:
        return session_to_out(session)

    @classmethod
    async def create_session(
        cls,
        user: User,
        data: GenerationSessionCreateRequest,
    ) -> AIGenerationSessionOut:
        await ensure_case_viewer(data.project_id, user)
        await cls._validate_create_input(data)
        if data.module_id is not None:
            exists = await ProjectModule.filter(
                id=data.module_id, project_id=data.project_id
            ).exists()
            if not exists:
                raise AppException("项目模块不存在", 404)

        requirement_text, knowledge_document_id, input_ref_type, input_ref_id = (
            await cls._resolve_session_requirement_text(data)
        )
        session = await AIGenerationSession.create(
            project_id=data.project_id,
            module_id=data.module_id,
            gen_type=GenType.functional,
            input_ref_type=input_ref_type,
            input_ref_id=input_ref_id,
            knowledge_document_id=knowledge_document_id,
            prompt_hash=compute_prompt_hash(requirement_text, data.user_prompt),
            status=SessionStatus.pending,
            user_prompt=data.user_prompt,
            created_by_id=user.id,
        )
        asyncio.create_task(
            cls._run_workflow(session.id, requirement_text, data.user_prompt)
        )
        return await cls._to_out(session)

    @classmethod
    async def _run_workflow(
        cls,
        session_id: int,
        requirement_text: str,
        user_prompt: str | None,
    ) -> None:
        session = await AIGenerationSession.get_or_none(id=session_id)
        if session is None:
            return
        session.status = SessionStatus.running
        await session.save(update_fields=["status"])
        try:
            if functional_gen_use_mock():
                payload = cls._mock_payload(requirement_text)
            elif not is_llm_configured():
                session.status = SessionStatus.failed
                session.error_message = LLM_NOT_CONFIGURED_MSG
                session.finished_at = datetime.now(timezone.utc)
                await session.save(
                    update_fields=["status", "error_message", "finished_at"]
                )
                return
            else:
                payload = await asyncio.to_thread(
                    cls._invoke_workflow, requirement_text, user_prompt
                )
            session.status = SessionStatus.success
            session.output_payload = payload
            session.finished_at = datetime.now(timezone.utc)
            session.error_message = None
            await session.save(
                update_fields=["status", "output_payload", "finished_at", "error_message"]
            )
        except Exception as exc:
            session.status = SessionStatus.failed
            session.error_message = str(exc) or repr(exc)
            session.finished_at = datetime.now(timezone.utc)
            await session.save(
                update_fields=["status", "error_message", "finished_at"]
            )

    @staticmethod
    def _mock_payload(requirement_text: str) -> dict:
        return {
            "test_points": [
                {
                    "type": "functional",
                    "dimension": "主流程",
                    "test_point": f"验证需求: {requirement_text[:80]}",
                }
            ],
            "cases": [
                {
                    "case_id": "TC-001",
                    "case_name": "mock 功能用例",
                    "priority": "P2",
                    "type": "functional",
                    "dimension": "主流程",
                    "preconditions": "系统已启动",
                    "test_steps": "1. 执行主流程",
                    "test_data": "",
                    "expected_result": "流程成功",
                    "actual_result": "",
                }
            ],
        }

    @staticmethod
    def _invoke_workflow(requirement_text: str, user_prompt: str | None) -> dict:
        from workflow.case_generator_workflow import GenerateTestCases

        graph = GenerateTestCases().create_workflow()
        config = {"configurable": {"thread_id": "functional-gen"}}
        result = graph.invoke(
            {"requirement": requirement_text, "user_prompt": user_prompt},
            config=config,
        )
        points = result.get("points") or []
        cases = result.get("test_cases") or []
        if isinstance(cases, str):
            import json

            cases = json.loads(cases)
        return {"test_points": points, "cases": cases}

    @classmethod
    async def get_session(cls, user: User, session_id: int) -> AIGenerationSessionOut:
        session = await cls._get_session_or_404(session_id)
        await ensure_case_viewer(session.project_id, user)
        return await cls._to_out(session)

    @classmethod
    async def update_preview(
        cls,
        user: User,
        session_id: int,
        data: GenerationPreviewUpdateRequest,
    ) -> AIGenerationSessionOut:
        session = await cls._get_session_or_404(session_id)
        await ensure_case_viewer(session.project_id, user)
        session.output_payload = data.output_payload
        await session.save(update_fields=["output_payload"])
        return await cls._to_out(session)

    @classmethod
    async def save_cases(
        cls,
        user: User,
        session_id: int,
        data: GenerationSaveRequest,
    ) -> GenerationSaveResult:
        session = await cls._get_session_or_404(session_id)
        await ensure_case_editor(session.project_id, user)
        if session.status != SessionStatus.success or not session.output_payload:
            raise AppException("生成会话未完成或无预览数据", 400)

        await CatalogService._get_catalog_or_404(data.catalog_id, session.project_id)
        cases = session.output_payload.get("cases") or []
        points = session.output_payload.get("test_points") or []
        requirement_id = data.requirement_id or session.input_ref_id

        created_case_ids: list[int] = []
        created_test_point_ids: list[int] = []

        async with in_transaction():
            point_map: dict[int, FunctionalTestPoint] = {}
            if requirement_id and points:
                for idx, pt in enumerate(points):
                    if not isinstance(pt, dict):
                        continue
                    tp = await FunctionalTestPoint.create(
                        requirement_id=requirement_id,
                        type=str(pt.get("type") or "functional"),
                        dimension=str(pt.get("dimension") or ""),
                        test_point=str(pt.get("test_point") or ""),
                        source=SourceType.ai,
                        generation_session_id=session.id,
                    )
                    point_map[idx] = tp
                    created_test_point_ids.append(tp.id)

            sort_base = await CaseService._next_sort_order(data.catalog_id)
            for order, idx in enumerate(data.case_indexes):
                if idx < 0 or idx >= len(cases):
                    raise AppException(f"无效的 case_index: {idx}", 400)
                item = cases[idx]
                if not isinstance(item, dict):
                    raise AppException(f"用例预览数据格式错误: index={idx}", 400)
                tp = point_map.get(idx) if requirement_id else None
                case = await FunctionalCase.create(
                    project_id=session.project_id,
                    module_id=session.module_id,
                    catalog_id=data.catalog_id,
                    requirement_id=requirement_id,
                    test_point_id=tp.id if tp else None,
                    case_no=str(item.get("case_id") or ""),
                    case_name=str(item.get("case_name") or f"AI用例-{idx + 1}"),
                    priority=_parse_priority(item.get("priority")),
                    dimension=str(item.get("dimension") or (tp.dimension if tp else "")),
                    type=FunctionalCaseType.functional,
                    preconditions=str(item.get("preconditions") or ""),
                    test_steps=str(item.get("test_steps") or ""),
                    test_data=str(item.get("test_data") or ""),
                    expected_result=str(item.get("expected_result") or ""),
                    actual_result=str(item.get("actual_result") or ""),
                    source=SourceType.ai,
                    exec_result=FunctionalExecResult.pending,
                    generation_session_id=session.id,
                    sort_order=sort_base + order,
                    created_by_id=user.id,
                    updated_by_id=user.id,
                )
                created_case_ids.append(case.id)

        return GenerationSaveResult(
            created_case_ids=created_case_ids,
            created_test_point_ids=created_test_point_ids,
        )
