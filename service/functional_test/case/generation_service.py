import asyncio
import os
from datetime import datetime, timezone

from tortoise.transactions import in_transaction

from service.ai_generation.common import (
    LLM_NOT_CONFIGURED_MSG,
    compute_prompt_hash,
    functional_gen_use_mock,
    is_llm_configured,
    load_knowledge_document_text,
)
from service.ai_generation.models import AIGenerationSession
from service.core.enums import (
    CaseCategory,
    GenType,
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
    async def _validate_create_input(cls, data: GenerationSessionCreateRequest) -> None:
        has_knowledge = data.knowledge_document_id is not None
        if not has_knowledge:
            raise AppException(
                "knowledge_document_id 至少提供一个",
                400,
            )

    @classmethod
    async def _resolve_session_document_text(
        cls,
        data: GenerationSessionCreateRequest,
    ) -> tuple[str, int | None]:
        if data.knowledge_document_id is not None:
            text = await load_knowledge_document_text(
                data.knowledge_document_id, data.project_id
            )
            return text, data.knowledge_document_id
        return "", None

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

        document_text, knowledge_document_id = (
            await cls._resolve_session_document_text(data)
        )
        session = await AIGenerationSession.create(
            project_id=data.project_id,
            module_id=data.module_id,
            gen_type=GenType.functional,
            knowledge_document_id=knowledge_document_id,
            prompt_hash=compute_prompt_hash(document_text, data.user_prompt),
            status=SessionStatus.pending,
            user_prompt=data.user_prompt,
            created_by_id=user.id,
        )
        asyncio.create_task(
            cls._run_workflow(session.id, document_text, data.user_prompt)
        )
        return await cls._to_out(session)

    @classmethod
    async def _run_workflow(
        cls,
        session_id: int,
        document_text: str,
        user_prompt: str | None,
    ) -> None:
        session = await AIGenerationSession.get_or_none(id=session_id)
        if session is None:
            return
        session.status = SessionStatus.running
        await session.save(update_fields=["status"])
        try:
            if functional_gen_use_mock():
                payload = cls._mock_payload(document_text)
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
                    cls._invoke_workflow, document_text, user_prompt
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
    def _mock_payload(document_text: str) -> dict:
        return {
            "test_points": [
                {
                    "type": "functional",
                    "dimension": "主流程",
                    "test_point": f"验证文档: {document_text[:80]}",
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
    def _invoke_workflow(document_text: str, user_prompt: str | None) -> dict:
        from workflow.case_generator_workflow import GenerateTestCases

        graph = GenerateTestCases().create_workflow()
        config = {"configurable": {"thread_id": "functional-gen"}}
        result = graph.invoke(
            {"document": document_text, "user_prompt": user_prompt},
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
    async def update_review(
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
        import traceback

        session = await cls._get_session_or_404(session_id)
        await ensure_case_editor(session.project_id, user)
        if session.status != SessionStatus.success or not session.output_payload:
            raise AppException("生成会话未完成或无预览数据", 400)

        # [DEBUG-问题6] 详细日志：保存前的关键信息
        print(f"[DEBUG-SAVE] session_id={session_id}, project_id={session.project_id}, catalog_id={data.catalog_id}")
        print(f"[DEBUG-SAVE] case_indexes={data.case_indexes}")
        
        await CatalogService._get_catalog_or_404(data.catalog_id, session.project_id)
        cases = session.output_payload.get("cases") or []
        points = session.output_payload.get("test_points") or []

        print(f"[DEBUG-SAVE] payload中 cases 数量={len(cases)}, points 数量={len(points)}")
        print(f"[DEBUG-SAVE] case_indexes 最大值={max(data.case_indexes) if data.case_indexes else 'N/A'}, cases长度={len(cases)}")

        created_case_ids: list[int] = []
        created_test_point_ids: list[int] = []

        try:
            async with in_transaction():
                point_map: dict[int, FunctionalTestPoint] = {}
                if points:
                    for idx, pt in enumerate(points):
                        if not isinstance(pt, dict):
                            continue
                        print(f"[DEBUG-SAVE] 创建测试点[{idx}]: type={pt.get('type')}, dimension={pt.get('dimension')}, test_point={str(pt.get('test_point', ''))[:50]}")
                        tp = await FunctionalTestPoint.create(
                            type=str(pt.get("type") or "functional"),
                            dimension=str(pt.get("dimension") or ""),
                            test_point=str(pt.get("test_point") or ""),
                            source=SourceType.ai,
                            generation_session_id=session.id,
                        )
                        point_map[idx] = tp
                        created_test_point_ids.append(tp.id)
                        print(f"[DEBUG-SAVE] 测试点创建成功, id={tp.id}")

                sort_base = await CaseService._next_sort_order(data.catalog_id)
                for order, idx in enumerate(data.case_indexes):
                    if idx < 0 or idx >= len(cases):
                        raise AppException(f"无效的 case_index: {idx}", 400)
                    item = cases[idx]
                    if not isinstance(item, dict):
                        raise AppException(f"用例预览数据格式错误: index={idx}", 400)
                    
                    print(f"[DEBUG-SAVE] 创建用例[order={order}, idx={idx}]: case_name={str(item.get('case_name', ''))[:50]}")
                    
                    # Map case to test point: use the same index (1:1 mapping)
                    tp = point_map.get(idx)
                    
                    def _to_str(val):
                        if isinstance(val, list):
                            return ' '.join(_to_str(item) for item in val)
                        return str(val or "")
                    
                    try:
                        case = await FunctionalCase.create(
                            project_id=session.project_id,
                            module_id=session.module_id,
                            catalog_id=data.catalog_id,
                            test_point_id=tp.id if tp else None,
                            case_no=_to_str(item.get("case_id")),
                            case_name=_to_str(item.get("case_name")) or f"AI用例-{idx + 1}",
                            priority=_parse_priority(item.get("priority")),
                            dimension=_to_str(item.get("dimension")) or (tp.dimension if tp else ""),
                            case_category=CaseCategory.functional,
                            preconditions=_to_str(item.get("preconditions")),
                            test_steps=_to_str(item.get("test_steps")),
                            test_data=_to_str(item.get("test_data")),
                            expected_result=_to_str(item.get("expected_result")),
                            source=SourceType.ai,
                            generation_session_id=session.id,
                            sort_order=sort_base + order,
                            created_by_id=user.id,
                            updated_by_id=user.id,
                        )
                        created_case_ids.append(case.id)
                        print(f"[DEBUG-SAVE] 用例创建成功, id={case.id}")
                    except Exception as case_err:
                        print(f"[DEBUG-SAVE] 用例创建失败[idx={idx}]: {case_err}")
                        print(f"[DEBUG-SAVE] 错误详情: {traceback.format_exc()}")
                        raise AppException(f"创建用例失败(idx={idx}): {str(case_err)}", 500)
        except Exception as txn_err:
            print(f"[DEBUG-SAVE] 事务异常: {txn_err}")
            print(f"[DEBUG-SAVE] 异常类型: {type(txn_err).__name__}")
            print(f"[DEBUG-SAVE] 完整堆栈:\n{traceback.format_exc()}")
            raise

        return GenerationSaveResult(
            created_case_ids=created_case_ids,
            created_test_point_ids=created_test_point_ids,
        )
