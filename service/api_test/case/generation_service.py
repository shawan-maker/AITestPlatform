"""接口测试模块 - case/generation_service

业务逻辑服务
"""
import asyncio
import json
import logging
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
    GenerationStatusOut,
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
from service.api_test.shared.interface_doc import interface_to_doc_dict, interface_to_doc_json
from service.core.enums import (
    ApiBaseCaseStatus,
    ApiCaseKind,
    CaseRunStatus,
    CaseRunType,
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

logger = logging.getLogger(__name__)


@dataclass
class _PreRunResult:
    """预执行结果"""
    index: int
    api_case: dict
    review_status: ReviewStatus
    error: str | None = None


class ApiCaseGenerationService:
    # 防止后台任务被 GC 回收
    """API用例generation服务"""
    _background_tasks: set = set()

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

    @staticmethod
    def _clean_dependency_name(name: str) -> str:
        """清理 AI 生成的依赖名称，去掉 method/path 前缀。

        "POST /member/public/login — 登录" → "登录"
        "GET /api/user - 获取用户" → "获取用户"
        "登录" → "登录"
        """
        # 匹配 "METHOD /path — name" 或 "METHOD /path - name"
        m = re.match(r'^[A-Z]+\s+\S+\s*[—\-]\s*(.+)$', name)
        if m:
            return m.group(1).strip()
        return name

    @staticmethod
    async def _get_all_project_interface_summaries(project_id: int) -> list[str]:
        """查询项目下所有接口的摘要列表，供 AI 识别依赖时使用。

        只返回 summary 名称（如 "登录"），不含 method/path，
        因为 AI 输出的 dependencies 会直接用这个名称，
        下游代码 (summary__in=dep_names) 也按 summary 字段查 DB。
        """
        from service.api_test.interface.models import ApiInterface
        interfaces = await ApiInterface.filter(
            project_id=project_id, is_current=True,
        ).only("method", "path", "summary")
        summaries = []
        for api in interfaces:
            name = (api.summary or "").strip()
            if name:
                summaries.append(name)
        return summaries

    @staticmethod
    async def enrich_preconditions_api_doc(
        project_id: int,
        selected_items: list[tuple[int, dict]],
        existing_docs: list[dict] | None = None,
    ) -> list[dict]:
        """按 base_case 的 dependencies 名称从 DB 补充前置依赖接口文档。

        复用自 _run_confirm_background 的逻辑，供 pipeline 等外部调用。
        如果 existing_docs 非空则直接返回，不做补充。
        """
        docs = list(existing_docs or [])
        if docs:
            return docs
        all_dep_names: list[str] = []
        seen: set[str] = set()
        for _, base in selected_items:
            for name in (base.get("dependencies") or []):
                name = ApiCaseGenerationService._clean_dependency_name(str(name).strip())
                if name and name not in seen:
                    all_dep_names.append(name)
                    seen.add(name)
        if not all_dep_names:
            return docs
        from service.api_test.interface.models import ApiInterface
        from service.api_test.shared.interface_doc import interface_to_doc_dict
        found = await ApiInterface.filter(
            project_id=project_id, summary__in=all_dep_names, is_current=True,
        )
        for iface in found:
            docs.append(interface_to_doc_dict(iface))
        logger.info("[enrich_preconditions] 从 DB 补充 %d 个前置接口文档", len(docs))
        return docs

    @classmethod
    async def preview(
        cls,
        user: User,
        interface_id: int,
        data: GeneratePreviewRequest,
    ) -> GeneratePreviewResult:
        """v3: 异步预览 — 立即返回 session_id，AI 生成在后台进行，前端通过轮询 generation-status 获取结果。"""
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_viewer(iface.project_id, user)
        resolved = await DependencyResolverService.resolve(iface.id)
        api_doc = interface_to_doc_json(iface)
        precoditions = resolved.precoditions_summaries

        # 无预配置依赖时，传入项目所有接口摘要，让 AI 自主识别依赖
        if not precoditions:
            precoditions = await cls._get_all_project_interface_summaries(iface.project_id)
            logger.info(
                "[preview] 无预配置依赖, 传入项目全部 %d 个接口摘要供 AI 识别依赖",
                len(precoditions),
            )

        session = await AIGenerationSession.create(
            project_id=iface.project_id,
            module_id=iface.module_id,
            gen_type=GenType.api_base,
            input_ref_type=InputRefType.interface,
            input_ref_id=iface.id,
            status=SessionStatus.running,
            user_prompt=None,
            prompt_hash=compute_prompt_hash(api_doc, None),
            source_channel=SourceChannel.interface_detail,
            created_by_id=user.id,
        )

        # 存储后台任务所需输入
        session.output_payload = {
            "api_doc": api_doc,
            "precoditions": precoditions,
            "precoditions_api_doc": resolved.precoditions_api_doc,
            "environment_id": data.environment_id,
        }
        await session.save(update_fields=["output_payload"])

        # 启动后台 AI 生成任务
        task = asyncio.create_task(cls._run_preview_background(session))
        cls._background_tasks.add(task)
        task.add_done_callback(cls._background_tasks.discard)

        # 立即返回，base_cases 为空，前端通过轮询获取结果
        return GeneratePreviewResult(session_id=session.id, base_cases=[])

    @classmethod
    async def _run_preview_background(cls, session: "AIGenerationSession") -> None:
        """后台执行 AI 用例生成，结果写入 session.output_payload。"""
        try:
            session = await AIGenerationSession.get(id=session.id)
            payload = session.output_payload or {}
            api_doc = payload.get("api_doc", "")
            precoditions = payload.get("precoditions", [])
            precoditions_api_doc = payload.get("precoditions_api_doc", [])
            environment_id = payload.get("environment_id")

            if api_test_gen_use_mock():
                base_cases = cls._mock_base_cases("preview")
            elif not is_llm_configured():
                session.status = SessionStatus.failed
                session.error_message = LLM_NOT_CONFIGURED_MSG
                session.finished_at = datetime.now(timezone.utc)
                await session.save(
                    update_fields=["status", "error_message", "finished_at"]
                )
                return
            else:
                base_cases = await asyncio.to_thread(
                    cls._invoke_basecase_workflow,
                    api_doc,
                    precoditions,
                    None,
                )

            session.status = SessionStatus.success
            session.output_payload = {
                "base_cases": base_cases,
                "api_doc": api_doc,
                "precoditions_api_doc": precoditions_api_doc,
                "environment_id": environment_id,
            }
            session.finished_at = datetime.now(timezone.utc)
            await session.save(
                update_fields=["status", "output_payload", "finished_at"]
            )
        except Exception as exc:
            logger.exception("后台预览生成失败 session=%s", session.id)
            session.status = SessionStatus.failed
            session.error_message = str(exc) or repr(exc)
            session.finished_at = datetime.now(timezone.utc)
            try:
                await session.save(
                    update_fields=["status", "error_message", "finished_at"]
                )
            except Exception:
                logger.error("保存失败状态也出错 session=%s", session.id)

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

        precoditions: list[str] = await cls._get_all_project_interface_summaries(data.project_id)
        if precoditions:
            logger.info(
                "[preview_from_doc] 传入项目全部 %d 个接口摘要供 AI 识别依赖",
                len(precoditions),
            )
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
                edited_base_cases=data.edited_base_cases,
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
        """v3: 异步确认 — 立即返回 session_id，预执行在后台进行，前端通过轮询获取进度。"""
        session = await cls._get_api_session_or_404(data.session_id)
        await ensure_api_editor(session.project_id, user)
        if session.status != SessionStatus.success or not session.output_payload:
            raise AppException("生成会话未完成", 400)

        # 环境可选：未选择时跳过预执行，直接保存为"待执行"
        if data.environment_id:
            env = await TestEnvironment.get_or_none(
                id=data.environment_id, project_id=session.project_id
            )
            if env is None:
                raise AppException("测试环境不存在", 404)

        base_cases = session.output_payload.get("base_cases") or []

        # 验证 selected_indexes
        for idx in data.selected_indexes:
            if idx < 0 or idx >= len(base_cases):
                raise AppException(f"无效的 selected_index: {idx}", 400)

        # 设置 session 为 running 状态，初始化进度信息
        session.status = SessionStatus.running
        session.finished_at = None
        progress_items = []
        for idx in data.selected_indexes:
            base = base_cases[idx]
            progress_items.append({
                "index": idx,
                "name": base.get("name", "") if isinstance(base, dict) else "",
                "status": "pending",
                "error": None,
            })
        session.output_payload["confirm_progress"] = {
            "total": len(data.selected_indexes),
            "completed": 0,
            "stage": "structuring",
            "items": progress_items,
        }
        session.output_payload["confirm_request"] = {
            "selected_indexes": data.selected_indexes,
            "environment_id": data.environment_id,
            "interface_id": data.interface_id,
            "catalog_id": data.catalog_id,
            "user_id": user.id,
            "edited_base_cases": data.edited_base_cases,
        }
        await session.save(update_fields=["status", "finished_at", "output_payload"])

        # 启动后台预执行任务
        task = asyncio.create_task(cls._run_confirm_background(session))
        cls._background_tasks.add(task)
        task.add_done_callback(cls._background_tasks.discard)

        return ApiConfirmResult(
            created_base_case_ids=[],
            created_case_ids=[],
            run_errors=[],
            created_interface_id=None,
        )

    @classmethod
    async def _run_confirm_background(cls, session: "AIGenerationSession") -> None:
        """后台执行预执行 + 创建DB记录，更新 session 进度。"""
        try:
            # 重新加载 session 以获取最新数据
            session = await AIGenerationSession.get(id=session.id)
            confirm_req = session.output_payload.get("confirm_request", {})
            selected_indexes = confirm_req.get("selected_indexes", [])
            environment_id = confirm_req.get("environment_id")
            interface_id = confirm_req.get("interface_id") or session.input_ref_id
            catalog_id = confirm_req.get("catalog_id")
            user_id = confirm_req.get("user_id")

            logger.info(
                "[预执行] session=%s 开始, selected=%d, env_id=%s",
                session.id, len(selected_indexes), environment_id,
            )

            user = await User.get_or_none(id=user_id)
            if user is None:
                raise AppException("用户不存在", 404)

            base_cases = session.output_payload.get("base_cases") or []

            # 合并用户编辑的基础用例（edited_base_cases 优先于原始 base_cases）
            edited = confirm_req.get("edited_base_cases")
            if edited and isinstance(edited, list):
                for i, edit_case in enumerate(edited):
                    if i < len(base_cases) and isinstance(edit_case, dict):
                        base_cases[i] = {**base_cases[i], **edit_case}

            created_interface_id = None
            if session.input_ref_type == InputRefType.interface:
                iface = await InterfaceService._get_current_or_404(interface_id)
                resolved = await DependencyResolverService.resolve(iface.id)
                precoditions_api_doc = resolved.precoditions_api_doc
            elif session.input_ref_type == InputRefType.api_doc:
                iface = await cls._create_interface_from_doc(
                    user,
                    project_id=session.project_id,
                    catalog_id=catalog_id,
                    api_doc_text=session.output_payload.get("api_doc") or "",
                    module_id=session.module_id,
                )
                created_interface_id = iface.id
                precoditions_api_doc = []
            else:
                raise AppException("不支持的生成会话类型", 400)

            api_doc = session.output_payload.get("api_doc") or interface_to_doc_json(iface)

            selected_items: list[tuple[int, dict]] = []
            for idx in selected_indexes:
                base = base_cases[idx]
                if not isinstance(base, dict):
                    continue
                selected_items.append((idx, base))

            created_base_ids: list[int] = []
            created_case_ids: list[int] = []
            run_errors: list[str] = []

            # ═══════════════════════════════════════════════════════
            # Phase 1: LLM 结构化（所有用例，含/不含环境都走此路径）
            # ═══════════════════════════════════════════════════════
            logger.info("[confirm] session=%s Phase1: 开始 LLM 结构化 %d 个用例", session.id, len(selected_items))

            # 补充前置依赖接口文档
            if not precoditions_api_doc:
                from service.api_test.shared.payload_builder import enrich_preconditions_api_doc
                all_dep_names: list[str] = []
                seen_names: set[str] = set()
                for idx, base in selected_items:
                    for name in (base.get("dependencies") or []):
                        name = cls._clean_dependency_name(str(name).strip())
                        if name and name not in seen_names:
                            all_dep_names.append(name)
                            seen_names.add(name)
                if all_dep_names:
                    from service.api_test.interface.models import ApiInterface
                    from service.api_test.shared.interface_doc import interface_to_doc_dict
                    found_ifaces = await ApiInterface.filter(
                        project_id=iface.project_id,
                        summary__in=all_dep_names,
                        is_current=True,
                    )
                    for found in found_ifaces:
                        precoditions_api_doc.append(interface_to_doc_dict(found))
                    logger.info("[confirm] 从 DB 补充 %d 个接口文档", len(precoditions_api_doc))

            # 加载环境数据（有环境时用于传给 LLM 做变量引用）
            test_env_data = None
            if environment_id:
                from service.test_execution.env_loader import load_test_env_data
                test_env_data = await load_test_env_data(environment_id)

            # 调用 LLM 结构化（skip_execution=True：只生成结构化用例，不执行）
            # 创建进度回调：每个用例完成后更新 session 进度供前端轮询
            loop = asyncio.get_running_loop()

            def _on_progress(completed: int, total: int, item: dict):
                """在 to_thread 线程中调用，更新 session 进度。"""
                session.output_payload["confirm_progress"]["completed"] = completed
                session.output_payload["confirm_progress"]["total"] = total
                asyncio.run_coroutine_threadsafe(
                    session.save(update_fields=["output_payload"]),
                    loop,
                )

            from service.ai_engine.shared.language_overlay import get_language_overlay
            _lang_overlay = get_language_overlay(session.output_language or "zh")
            pre_run_results = await cls._pre_run_selected_base_cases(
                selected_items=selected_items,
                api_doc=api_doc,
                precoditions_api_doc=precoditions_api_doc,
                environment_id=environment_id or 0,
                project_id=iface.project_id,
                test_env_data=test_env_data,
                skip_execution=True,
                progress_callback=_on_progress,
                language_overlay=_lang_overlay,
            )
            logger.info("[confirm] session=%s Phase1: LLM 结构化完成, results=%d", session.id, len(pre_run_results))

            # 收集 AI 生成的前置步骤
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

            # ★ 变量对齐：两阶段（单用例内部 + 跨用例），覆盖 URL/request/headers
            cls._align_variable_names(ai_precondition_map, pre_run_results)

            # 创建前置操作用例
            precondition_map = await cls._create_precondition_cases(
                interface=iface,
                base_cases=base_cases,
                selected_indexes=[idx for idx, _ in selected_items],
                precoditions_api_doc=precoditions_api_doc,
                environment_id=environment_id,
                test_env_data=test_env_data,
                user_id=user.id,
                session_id=session.id,
                ai_precondition_map=ai_precondition_map,
            )

            # ═══════════════════════════════════════════════════════
            # Phase 1 续: 保存结构化用例到 DB
            # ═══════════════════════════════════════════════════════
            initial_exec_status = ExecStatus.running if environment_id else ExecStatus.pending

            async with in_transaction():
                sort_base = await cls._next_case_sort_order(iface.id, ApiCaseKind.main)
                for order, pre_result in enumerate(pre_run_results):
                    idx = pre_result.index
                    base = base_cases[idx]

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

                    main_payload = dict(pre_result.api_case) if isinstance(pre_result.api_case, dict) else {}
                    if precondition_map:
                        main_payload["preconditions"] = []
                        dep_names = [cls._clean_dependency_name(str(d).strip()) for d in (base.get("dependencies") or [])]
                        main_payload["precondition_ids"] = [
                            precondition_map[n] for n in dep_names if n in precondition_map
                        ]

                    case_row = await ApiTestCase.create(
                        project_id=iface.project_id,
                        module_id=iface.module_id,
                        base_case_id=base_row.id,
                        interface_id=iface.id,
                        title=str(pre_result.api_case.get("title") or base.get("name") or base_row.name) if isinstance(pre_result.api_case, dict) else base_row.name,
                        case_kind=ApiCaseKind.main,
                        sort_order=sort_base + order,
                        case_payload=main_payload,
                        review_status=pre_result.review_status if isinstance(pre_result.review_status, ReviewStatus) else ReviewStatus.init,
                        exec_status=initial_exec_status,
                        environment_id=environment_id,
                        generation_session_id=session.id,
                        created_by_id=user.id,
                        updated_by_id=user.id,
                    )
                    created_case_ids.append(case_row.id)

            # Phase 1 完成：标记 session 为 success，前端可关闭弹窗
            session.output_payload["confirm_result"] = {
                "created_base_case_ids": created_base_ids,
                "created_case_ids": created_case_ids,
                "run_errors": [],
                "created_interface_id": created_interface_id,
                "created_precondition_ids": list(precondition_map.values()) if precondition_map else [],
            }
            session.output_payload["confirm_progress"]["completed"] = len(selected_items)
            session.output_payload["confirm_progress"]["stage"] = "structuring_done"
            session.status = SessionStatus.success
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["status", "output_payload", "finished_at"])
            logger.info("[confirm] session=%s Phase1 完成, cases=%d, 状态=success", session.id, len(created_case_ids))

            # ═══════════════════════════════════════════════════════
            # Phase 2: 异步预执行（仅在有环境时）
            # ═══════════════════════════════════════════════════════
            if environment_id and created_case_ids:
                asyncio.create_task(
                    cls._execute_cases_async(
                        case_ids=created_case_ids,
                        environment_id=environment_id,
                        user_id=user.id,
                    )
                )
                logger.info("[confirm] session=%s Phase2: 已启动异步预执行 %d 个用例", session.id, len(created_case_ids))

        except Exception as exc:
            logger.exception("后台预执行失败 session=%s", session.id)
            session.status = SessionStatus.failed
            session.error_message = str(exc)
            session.finished_at = datetime.now(timezone.utc)
            try:
                await session.save(update_fields=["status", "error_message", "finished_at"])
            except Exception:
                logger.error("保存失败状态也出错 session=%s", session.id)

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

        from service.ai_engine.parsers.api_document_ai_parser import APIDocumentParser

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
    def _build_precondition_payload(dep_name: str, dep_doc: dict) -> dict:
        """从依赖接口文档构建 precondition 用例的基础 payload。
        根据 requestBody.content_type 正确选择 request.data / request.json。
        """
        from service.api_test.shared.payload_builder import _normalize_template_vars, _normalize_in_structure

        method = (dep_doc.get("method") or "GET").upper()
        path = _normalize_template_vars(dep_doc.get("path") or "")
        parameters = dep_doc.get("parameters") or {}
        request_body = dep_doc.get("requestBody")

        payload: dict = {
            "title": dep_name,
            "method": method,
            "path": path,
            "interface": {"url": path, "method": method.lower()},
            "headers": {},
            "request": {},
            "setup_script": "",
            "teardown_script": "",
            "extract": [],
            "assertions": [],
        }

        # ---- 处理 query/path 参数 ----
        query_params = {}
        if isinstance(parameters, dict):
            for pname, pinfo in parameters.items():
                if not isinstance(pinfo, dict):
                    continue
                p_in = (pinfo.get("in") or "query").lower()
                if p_in in ("query", "path"):
                    query_params[pname] = pinfo.get("example") or pinfo.get("default") or ""
        elif isinstance(parameters, list):
            for p in parameters:
                if isinstance(p, dict) and p.get("in") == "query":
                    query_params[p.get("name", "")] = p.get("example") or ""
        if query_params:
            payload["request"]["params"] = _normalize_in_structure(query_params)

        # ---- 处理请求体：根据 content_type 选择 data / json ----
        content_type = ""
        body_fields: dict[str, str] = {}

        if isinstance(request_body, dict) and request_body:
            content_type = (request_body.get("content_type") or "").lower()
            raw_body = request_body.get("body") or []

            if isinstance(raw_body, list):
                # 结构化格式：body 是 [{name, type, ...}, ...]
                for field in raw_body:
                    if isinstance(field, dict):
                        fname = field.get("name") or ""
                        fval = field.get("example") or field.get("default") or ""
                        if fname:
                            body_fields[fname] = fval
            elif isinstance(raw_body, dict):
                # 已经是 key-value 格式
                body_fields = {k: (v if isinstance(v, str) else "") for k, v in raw_body.items()}

        # 同时处理 parameters 中的 formData 类型参数
        if isinstance(parameters, dict):
            for pname, pinfo in parameters.items():
                if not isinstance(pinfo, dict):
                    continue
                p_in = (pinfo.get("in") or "").lower()
                if p_in == "formdata":
                    body_fields[pname] = pinfo.get("example") or pinfo.get("default") or ""
                    if not content_type:
                        content_type = "application/x-www-form-urlencoded"

        # 根据 content_type 放入正确的 request key（归一化 {var} → ${var}）
        if body_fields:
            normalized_body = _normalize_in_structure(body_fields)
            if "form-urlencoded" in content_type or "multipart" in content_type:
                payload["headers"]["Content-Type"] = content_type or "application/x-www-form-urlencoded"
                payload["request"]["data"] = normalized_body
            else:
                # 默认 JSON
                ct = content_type if "json" in content_type else "application/json"
                payload["headers"]["Content-Type"] = ct
                payload["request"]["json"] = normalized_body

        return payload

    @classmethod
    async def _create_precondition_cases(
        cls,
        *,
        interface,
        base_cases: list[dict],
        selected_indexes: list[int],
        precoditions_api_doc: list[dict],
        environment_id: int | None,
        test_env_data: dict | None,
        user_id: int,
        session_id: int,
        ai_precondition_map: dict[str, dict] | None = None,
    ) -> dict[str, int]:
        """
        为所有选中 base_case 的 dependencies 创建 precondition 用例。
        返回 {dependency名称: 用例ID} 映射。
        """
        # 1. 收集所有不重复的 dependency 名称
        all_dep_names: list[str] = []
        seen: set[str] = set()
        for idx in selected_indexes:
            if idx >= len(base_cases):
                continue
            for name in (base_cases[idx].get("dependencies") or []):
                name = cls._clean_dependency_name(str(name).strip())
                if name and name not in seen:
                    all_dep_names.append(name)
                    seen.add(name)
        if not all_dep_names:
            return {}

        # 2. 过滤已存在的 precondition 用例（同接口下同名则跳过）
        existing = await ApiTestCase.filter(
            interface_id=interface.id,
            case_kind=ApiCaseKind.precondition,
            title__in=all_dep_names,
        ).values_list("title", flat=True)
        existing_set = set(existing)
        new_dep_names = [n for n in all_dep_names if n not in existing_set]
        if not new_dep_names:
            logger.info("[precondition] 所有依赖用例已存在，跳过创建")
            return {}

        # 3. dependency 名称 → 接口文档映射
        dep_doc_by_summary: dict[str, dict] = {}
        for doc in (precoditions_api_doc or []):
            summary = doc.get("summary") or ""
            if summary:
                dep_doc_by_summary[summary] = doc

        # 4. 生成 precondition 用例（程序化构建，不调用 AI workflow）
        sort_base = await cls._next_case_sort_order(interface.id, ApiCaseKind.precondition)
        created_map: dict[str, int] = {}

        for order, dep_name in enumerate(new_dep_names):
            dep_doc = dep_doc_by_summary.get(dep_name)
            case_title = dep_name  # 默认用 DB 接口名，AI 有翻译时会被覆盖

            # 如果 precoditions_api_doc 中找不到，尝试按 summary 查数据库
            if dep_doc is None:
                found_iface = await ApiInterface.filter(
                    project_id=interface.project_id,
                    summary=dep_name,
                    is_current=True,
                ).first()
                if found_iface:
                    dep_doc = interface_to_doc_dict(found_iface)
                else:
                    dep_doc = {
                        "method": "GET",
                        "path": "",
                        "summary": dep_name,
                        "parameters": {},
                        "requestBody": None,
                    }

            # 优先用 AI 生成的前置步骤数据（含变量引用、提取、断言）
            ai_step = (ai_precondition_map or {}).get(dep_name)
            # 精确匹配失败时，尝试子串匹配（LLM 生成的标题可能与依赖名不完全一致）
            if not ai_step and ai_precondition_map:
                for _ai_key, _ai_val in ai_precondition_map.items():
                    if dep_name in _ai_key or _ai_key in dep_name:
                        ai_step = _ai_val
                        logger.info("[precondition] 子串匹配: dep_name='%s' → ai_key='%s'", dep_name, _ai_key)
                        break
            if ai_step:
                from service.api_test.shared.payload_builder import _convert_precondition, _normalize_template_vars
                case_payload = _convert_precondition(ai_step)
                # 优先使用 AI 生成的标题（英文模式下已翻译），否则用 DB 接口名
                case_payload["title"] = (ai_step.get("title") or dep_name).strip() or dep_name
                case_title = case_payload["title"]
                # Override URL/method with actual interface data from DB (AI may guess wrong)
                # Normalize {var} → ${var} so the engine can replace them at runtime
                if dep_doc and dep_doc.get("path"):
                    case_payload["path"] = _normalize_template_vars(dep_doc["path"])
                    case_payload["method"] = (dep_doc.get("method") or "GET").upper()
                # Fix Content-Type header and body placement from actual interface params
                if dep_doc:
                    actual_ct = ""
                    for param in (dep_doc.get("parameters") or []):
                        if isinstance(param, dict) and param.get("in") == "header" and \
                           (param.get("name") or "").lower() == "content-type":
                            actual_ct = param.get("default") or param.get("example") or ""
                            break
                    if not actual_ct and dep_doc.get("requestBody"):
                        rb = dep_doc["requestBody"]
                        if isinstance(rb, dict):
                            content = rb.get("content") or {}
                            if "application/json" in content:
                                actual_ct = "application/json"
                            elif "application/x-www-form-urlencoded" in content:
                                actual_ct = "application/x-www-form-urlencoded"
                            elif "multipart/form-data" in content:
                                actual_ct = "multipart/form-data"
                    if actual_ct:
                        headers = case_payload.get("headers") or {}
                        headers["Content-Type"] = actual_ct
                        case_payload["headers"] = headers
                        # Fix body placement based on actual Content-Type
                        request = case_payload.get("request") or {}
                        if "application/json" in actual_ct:
                            if "data" in request and "json" not in request:
                                request["json"] = request.pop("data")
                        else:
                            if "json" in request and "data" not in request:
                                request["data"] = request.pop("json")
                        case_payload["request"] = request
                # Update interface sub-object to match corrected path/method
                iface_sub = case_payload.get("interface") or {}
                iface_sub["url"] = case_payload.get("path", "")
                iface_sub["method"] = (case_payload.get("method") or "GET").lower()
                case_payload["interface"] = iface_sub

                # ── 变量名归一化：setup_script 保存的变量名 vs URL/request 引用的变量名 ──
                # URL 已从 DB 接口文档覆盖，以 URL 中的 ${var} 为准，修正 setup_script
                _setup = case_payload.get("setup_script") or ""
                _var_ref_re = re.compile(r'\$\{([^}]+)\}')
                _save_var_re = re.compile(r'save_env_variable\s*\(\s*["\']([^"\']+)["\']')
                _saved = _save_var_re.findall(_setup)
                if _saved:
                    _refs = set(_var_ref_re.findall(iface_sub.get("url", "")))
                    _refs.update(_var_ref_re.findall(str(case_payload.get("request") or {})))
                    _refs.update(_var_ref_re.findall(str(case_payload.get("headers") or {})))
                    logger.info("[precondition] 变量归一化入口: dep=%s, url=%s, saved=%s, refs=%s",
                                dep_name, iface_sub.get("url", ""), _saved, _refs)
                    # 用语义匹配找到 ref→saved_var 映射，再反转为 saved_var→ref
                    _ref_to_sv = cls._build_var_replacements(case_payload, _saved, _refs)
                    logger.info("[precondition] 变量归一化结果: dep=%s, ref_to_sv=%s", dep_name, _ref_to_sv)
                    _sv_to_ref = {sv: ref for ref, sv in _ref_to_sv.items()}
                    if _sv_to_ref:
                        for old_name, new_name in _sv_to_ref.items():
                            _setup = _setup.replace(
                                f'save_env_variable("{old_name}"', f'save_env_variable("{new_name}"')
                            _setup = _setup.replace(
                                f"save_env_variable('{old_name}'", f"save_env_variable('{new_name}'")
                            _setup = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, _setup)
                        case_payload["setup_script"] = _setup
                        logger.info("[precondition] 变量归一化 '%s': %s", dep_name, _sv_to_ref)

                logger.info(
                    "[precondition] 使用 AI 数据构建: %s, assertions=%d, extract=%d",
                    dep_name,
                    len(case_payload.get("assertions") or []),
                    len(case_payload.get("extract") or []),
                )
            else:
                # 降级：从接口文档程序化构建
                case_payload = cls._build_precondition_payload(dep_name, dep_doc)
                logger.info("[precondition] 降级构建: %s (无 AI 数据)", dep_name)

            case_row = await ApiTestCase.create(
                project_id=interface.project_id,
                module_id=interface.module_id,
                interface_id=interface.id,
                title=case_title,
                case_kind=ApiCaseKind.precondition,
                sort_order=sort_base + order,
                case_payload=case_payload,
                review_status=ReviewStatus.init,
                exec_status=ExecStatus.pending,
                environment_id=environment_id,
                generation_session_id=session_id,
                created_by_id=user_id,
                updated_by_id=user_id,
            )
            created_map[dep_name] = case_row.id
            logger.info("[precondition] 创建用例 id=%d title=%s", case_row.id, dep_name)

        return created_map

    @staticmethod
    def _split_precondition_exec_data(
        precondition_steps: list[dict],
        merged_assert_info: list[dict],
        merged_extract_info: list[dict],
    ) -> tuple[dict[str, list], dict[str, list]]:
        """Split merged assert_info / extract_info by precondition step.

        Engine (BaseCase.perform) appends assertion/extraction results from
        precondition steps and the main case into a single flat list.
        This method walks the precondition tree in DFS order (same as the engine)
        and slices the merged lists so each precondition step gets its own portion.

        Returns:
            (assert_info_by_title, extract_info_by_title)
        """

        def _count_tree(steps) -> tuple[int, int]:
            """Total (assertions, extractions) in the entire sub-tree."""
            a, e = 0, 0
            for s in steps:
                if not isinstance(s, dict):
                    continue
                sub = s.get("preconditions")
                if sub and isinstance(sub, list):
                    sa, se = _count_tree(sub)
                    a += sa
                    e += se
                a += len(s.get("assertions") or [])
                e += len(s.get("extract") or [])
            return a, e

        def _walk(steps, pre_list, extract_list, pos_a, pos_e, a_by_title, e_by_title):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                title = (step.get("title") or "").strip()
                # Nested preconditions first (engine DFS order)
                sub = step.get("preconditions")
                if sub and isinstance(sub, list):
                    _walk(sub, pre_list, extract_list, pos_a, pos_e, a_by_title, e_by_title)
                    # Advance positions by entire sub-tree totals
                    sub_a, sub_e = _count_tree(sub)
                    pos_a += sub_a
                    pos_e += sub_e

                n_assert = len(step.get("assertions") or [])
                n_extract = len(step.get("extract") or [])

                if title:
                    a_by_title[title] = pre_list[pos_a : pos_a + n_assert]
                    e_by_title[title] = extract_list[pos_e : pos_e + n_extract]

                pos_a += n_assert
                pos_e += n_extract

        assert_by_title: dict[str, list] = {}
        extract_by_title: dict[str, list] = {}
        _walk(
            precondition_steps,
            merged_assert_info,
            merged_extract_info,
            0, 0,
            assert_by_title,
            extract_by_title,
        )
        return assert_by_title, extract_by_title

    @classmethod
    async def _update_precondition_results_from_pre_run(
        cls,
        precondition_map: dict[str, int],
        pre_run_results: list,
    ) -> None:
        """从 workflow 预执行结果中解析前置步骤数据，更新 DB 前置用例。

        引擎 (BaseCase) 现在为每个前置步骤记录独立的执行结果
        （precondition_results），包含 response_body、request_body、
        assert_info 等完整数据。
        """
        # 合并所有 pre_run_results 的 log_data 和 precondition_results
        all_logs: list = []
        pre_step_data: dict[str, dict] = {}  # title → per-step engine result

        for r in pre_run_results:
            er = r.exec_result or {}
            if isinstance(er, dict):
                cases = er.get("cases") or []
                if cases and isinstance(cases, list):
                    for c in cases:
                        if isinstance(c, dict):
                            all_logs.extend(c.get("log_data") or [])
                            for ps in (c.get("precondition_results") or []):
                                t = (ps.get("title") or "").strip()
                                if t:
                                    pre_step_data[t] = ps
                all_logs.extend(er.get("log_data") or [])
                for ps in (er.get("precondition_results") or []):
                    t = (ps.get("title") or "").strip()
                    if t:
                        pre_step_data[t] = ps

        if pre_step_data:
            for _t, _s in pre_step_data.items():
                logger.info(
                    "[precondition] per-step 数据: title=%s, status_code=%s, "
                    "assert_info=%d, extract_info=%d, has_response_body=%s",
                    _t, _s.get("status_code"),
                    len(_s.get("assert_info") or []),
                    len(_s.get("extract_info") or []),
                    bool(_s.get("response_body")),
                )
        else:
            logger.warning(
                "[precondition] exec_result 中未找到 precondition_results，"
                "可能引擎版本较旧，回退到日志解析模式"
            )

        # 解析前置步骤结果（从日志）
        pre_status: dict[str, str] = {}  # title → "success" | "fail"
        pre_logs: dict[str, list] = {}   # title → [(level, msg), ...]
        current_title = None

        for entry in all_logs:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                continue
            level = str(entry[0])
            msg = " ".join(str(x) for x in entry[1:])

            if "执行前置步骤:" in msg:
                current_title = msg.split("执行前置步骤:")[-1].strip()
                pre_logs.setdefault(current_title, [])
            elif current_title:
                pre_logs.setdefault(current_title, []).append([level, msg])

            if "前置完成:" in msg:
                title = msg.split("前置完成:")[-1].strip()
                pre_status[title] = "success"
            elif "前置失败:" in msg or "前置执行异常:" in msg:
                parts = msg.split(":")
                if len(parts) >= 2:
                    title = parts[-1].strip().split("—")[0].strip()
                    pre_status.setdefault(title, "fail")

        # 更新各 DB 前置用例
        for dep_name, pre_id in precondition_map.items():
            try:
                pre_case = await ApiTestCase.get(id=pre_id)
            except Exception:
                continue

            status = pre_status.get(dep_name)
            logs = pre_logs.get(dep_name, [])
            step = pre_step_data.get(dep_name, {})

            # 从 per-step 数据推断状态（如果日志中未找到）
            if status is None and step:
                sc = step.get("status_code", "")
                status = "success" if str(sc).startswith("2") else "fail"
            elif status is None:
                all_success = all(
                    r.review_status == ReviewStatus.success for r in pre_run_results
                )
                status = "success" if all_success else "fail"

            payload_copy = dict(pre_case.case_payload)

            pre_case.exec_status = (
                ExecStatus.success if status == "success" else ExecStatus.fail
            )
            payload_copy["_exec_result"] = {
                "status": status,
                "response_code": step.get("status_code", ""),
                "response_body": step.get("response_body"),
                "response_headers": step.get("response_headers", {}),
                "request_headers": step.get("request_headers") or payload_copy.get("headers") or {},
                "request_body": step.get("request_body"),
                "method": step.get("method", ""),
                "url": step.get("url", ""),
                "run_time": step.get("run_time", 0),
                "log_data": logs,
                "assert_info": step.get("assert_info") or [],
                "extract_info": step.get("extract_info") or [],
            }
            pre_case.case_payload = payload_copy
            await pre_case.save(
                update_fields=["exec_status", "case_payload", "updated_at"],
            )
            logger.info(
                "[precondition] 更新用例结果 id=%s title=%s → %s (step_data=%s)",
                pre_id, dep_name, status, "有" if step else "无",
            )

    @staticmethod
    def _invoke_basecase_workflow(
        api_doc: str,
        precoditions: list[str],
        user_prompt: str | None = None,
    ) -> list[dict]:
        from service.ai_engine.workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow

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

    @staticmethod
    def _get_ref_param_context(case: dict, var_pattern) -> dict[str, set[str]]:
        """构建 ${ref} → 所在参数名集合 的映射，用于语义匹配。

        例：request.data.phone = "${p}" → {"p": {"phone"}}
        """
        ctx: dict[str, set[str]] = {}
        for section in ("data", "params", "json"):
            body = (case.get("request") or {}).get(section)
            if isinstance(body, dict):
                for param_name, param_value in body.items():
                    if isinstance(param_value, str):
                        for ref in var_pattern.findall(param_value):
                            ctx.setdefault(ref, set()).add(param_name.lower())
        # URL 路径参数
        url = (case.get("interface") or {}).get("url", "") or case.get("path", "")
        for ref in var_pattern.findall(url):
            ctx.setdefault(ref, set()).add(f"url:{ref}")
        return ctx

    @staticmethod
    def _build_var_replacements(case: dict, saved_vars: list[str], refs: set[str]) -> dict[str, str]:
        """语义匹配：为不匹配的 ${ref} 找到正确的 saved_var，返回替换映射。

        匹配策略（优先级从高到低）：
        1. 语义匹配：ref 所在的参数名 与 saved_var 名称有包含关系
        2. 前缀匹配：仅在唯一候选时生效（降级策略）
        """
        var_pattern = re.compile(r'\$\{([^}]+)\}')
        saved_set = set(saved_vars)
        param_ctx = ApiCaseGenerationService._get_ref_param_context(case, var_pattern)
        replacements = {}
        for ref in refs:
            if ref in saved_set:
                continue

            # 策略 1：语义匹配 — 参数名上下文
            ref_params = param_ctx.get(ref, set())
            semantic_match = None
            for sv in saved_vars:
                sv_lower = sv.lower()
                for p in ref_params:
                    # 参数名与变量名有包含关系
                    if p in sv_lower or sv_lower in p:
                        semantic_match = sv
                        break
                if semantic_match:
                    break

            if semantic_match:
                replacements[ref] = semantic_match
                continue

            # 策略 2：前缀匹配（仅唯一候选时）
            candidates = [sv for sv in saved_vars if sv.startswith(ref) and sv != ref]
            if len(candidates) == 1:
                replacements[ref] = candidates[0]
            elif not candidates:
                for sv in saved_vars:
                    if ref.startswith(sv) and len(ref) > len(sv):
                        replacements[ref] = sv
                        break

            # 策略 3：词边界匹配 — ref 作为 _ 分隔的段出现在 saved_var 中（仅唯一候选时）
            # 例: ref="r", saved_var="verify_r" → segments=["verify","r"] → 匹配
            if ref not in replacements:
                segment_candidates = []
                for sv in saved_vars:
                    parts = sv.split('_')
                    if len(parts) > 1 and ref in parts:
                        segment_candidates.append(sv)
                if len(segment_candidates) == 1:
                    replacements[ref] = segment_candidates[0]

        return replacements

    @staticmethod
    def _align_variable_names(
        ai_precondition_map: dict[str, dict],
        pre_run_results: list,
    ) -> None:
        """后处理：对齐变量引用（两阶段）。

        Phase 1 - 单用例内部对齐：
            每个前置用例的 setup_script 保存的变量名 vs 同用例 URL/request 引用的变量名。
            解决：setup_script 保存 r_num 但 URL 引用 ${r} 的问题。

        Phase 2 - 跨用例对齐：
            前置用例保存的变量名 vs 主用例中引用的变量名。
            利用 API 参数名作为上下文信号（同参数名 = 同变量）。
        """
        if not ai_precondition_map and not pre_run_results:
            return

        var_pattern = re.compile(r'\$\{([^}]+)\}')
        save_pattern = re.compile(r'save_env_variable\s*\(\s*["\']([^"\']+)["\']')
        total_replacements = 0

        # ── 通用工具函数 ──
        def _get_saved_vars(script: str) -> list[str]:
            return save_pattern.findall(script or "")

        def _get_all_refs(obj) -> set:
            """递归收集所有 ${var} 引用"""
            refs = set()
            if isinstance(obj, str):
                refs.update(var_pattern.findall(obj))
            elif isinstance(obj, dict):
                for v in obj.values():
                    refs.update(_get_all_refs(v))
            elif isinstance(obj, list):
                for item in obj:
                    refs.update(_get_all_refs(item))
            return refs

        def _replace_refs_in(obj, replacements: dict):
            """递归替换 ${old} → ${new}"""
            if isinstance(obj, str):
                for old, new in replacements.items():
                    obj = obj.replace(f"${{{old}}}", f"${{{new}}}")
                return obj
            elif isinstance(obj, dict):
                return {k: _replace_refs_in(v, replacements) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_replace_refs_in(item, replacements) for item in obj]
            return obj

        def _apply_replacements(case: dict, replacements: dict):
            """对单个用例的 URL、request、headers、scripts 执行替换"""
            nonlocal total_replacements
            if not replacements:
                return
            count_before = total_replacements
            # URL
            iface = case.get("interface") or {}
            if iface.get("url"):
                new_url = _replace_refs_in(iface["url"], replacements)
                if new_url != iface["url"]:
                    iface["url"] = new_url
                    total_replacements += 1
            if case.get("path"):
                new_path = _replace_refs_in(case["path"], replacements)
                if new_path != case["path"]:
                    case["path"] = new_path
            # Request
            req = case.get("request")
            if req and isinstance(req, dict):
                new_req = _replace_refs_in(req, replacements)
                if new_req != req:
                    case["request"] = new_req
                    total_replacements += 1
            # Headers
            headers = case.get("headers")
            if headers and isinstance(headers, dict):
                new_h = _replace_refs_in(headers, replacements)
                if new_h != headers:
                    case["headers"] = new_h
                    total_replacements += 1
            # Scripts
            for sf in ('setup_script', 'teardown_script'):
                script = case.get(sf) or ""
                new_script = _replace_refs_in(script, replacements)
                if new_script != script:
                    case[sf] = new_script
                    total_replacements += 1
            added = total_replacements - count_before

        # ═══════════════════════════════════════════════════
        # Phase 1: 单用例内部对齐（前置用例自身）
        # ═══════════════════════════════════════════════════
        for title, pre in (ai_precondition_map or {}).items():
            if not isinstance(pre, dict):
                continue
            saved_vars = _get_saved_vars(pre.get("setup_script") or "")
            if not saved_vars:
                continue

            # 收集此用例 URL + request + headers 中的所有引用
            refs = set()
            iface = pre.get("interface") or {}
            refs.update(_get_all_refs(iface.get("url", "")))
            refs.update(_get_all_refs(pre.get("path", "")))
            refs.update(_get_all_refs(pre.get("request") or {}))
            refs.update(_get_all_refs(pre.get("headers") or {}))

            replacements = ApiCaseGenerationService._build_var_replacements(pre, saved_vars, refs)
            _apply_replacements(pre, replacements)

        # ═══════════════════════════════════════════════════
        # Phase 1.5: 主用例自身的 setup_script vs URL 对齐
        # ═══════════════════════════════════════════════════
        for result in pre_run_results:
            case = result.api_case if hasattr(result, 'api_case') else None
            if not isinstance(case, dict):
                continue
            saved_vars = _get_saved_vars(case.get("setup_script") or "")
            if not saved_vars:
                continue

            refs = set()
            iface = case.get("interface") or {}
            refs.update(_get_all_refs(iface.get("url", "")))
            refs.update(_get_all_refs(case.get("path", "")))
            refs.update(_get_all_refs(case.get("request") or {}))
            refs.update(_get_all_refs(case.get("headers") or {}))

            replacements = ApiCaseGenerationService._build_var_replacements(case, saved_vars, refs)
            _apply_replacements(case, replacements)

            _apply_replacements(case, replacements)

        # ═══════════════════════════════════════════════════
        # Phase 2: 跨用例对齐（前置 → 主用例）
        # ═══════════════════════════════════════════════════
        # 构建前置变量上下文：变量名 → API 参数名集合
        saved_var_contexts: dict[str, set[str]] = {}
        for title, pre in (ai_precondition_map or {}).items():
            if not isinstance(pre, dict):
                continue
            saved_in_this = set(_get_saved_vars(pre.get("setup_script") or ""))

            # request body 中的引用 → 参数名上下文
            request = pre.get("request") or {}
            for section in ("data", "params", "json"):
                body = request.get(section)
                if not isinstance(body, dict):
                    continue
                for param_name, param_value in body.items():
                    if not isinstance(param_value, str):
                        continue
                    for ref in var_pattern.findall(param_value):
                        if ref in saved_in_this:
                            saved_var_contexts.setdefault(ref, set()).add(param_name.lower())

            # headers 中的引用
            headers = pre.get("headers") or {}
            if isinstance(headers, dict):
                for header_name, header_value in headers.items():
                    if isinstance(header_value, str):
                        for ref in var_pattern.findall(header_value):
                            if ref in saved_in_this:
                                saved_var_contexts.setdefault(ref, set()).add(
                                    f"header:{header_name.lower()}"
                                )

        if not saved_var_contexts:
            return

        for result in pre_run_results:
            case = result.api_case if hasattr(result, 'api_case') else None
            if not isinstance(case, dict):
                continue

            local_vars: set[str] = set()
            for sf in ('setup_script', 'teardown_script'):
                local_vars.update(save_pattern.findall(case.get(sf) or ""))
            all_known = set(saved_var_contexts.keys()) | local_vars

            # request body 参数上下文匹配
            request = case.get("request") or {}
            for section in ("data", "params", "json"):
                body = request.get(section)
                if not isinstance(body, dict):
                    continue
                for param_name, param_value in body.items():
                    if not isinstance(param_value, str):
                        continue
                    for ref in var_pattern.findall(param_value):
                        if ref in all_known:
                            continue
                        ctx = param_name.lower()
                        for saved_var, saved_ctxs in saved_var_contexts.items():
                            if ctx in saved_ctxs:
                                body[param_name] = param_value.replace(
                                    f"${{{ref}}}", f"${{{saved_var}}}")
                                total_replacements += 1
                                break

            # headers 上下文匹配
            headers = case.get("headers") or {}
            if isinstance(headers, dict):
                for header_name, header_value in list(headers.items()):
                    if not isinstance(header_value, str):
                        continue
                    for ref in var_pattern.findall(header_value):
                        if ref in all_known:
                            continue
                        ctx = f"header:{header_name.lower()}"
                        for saved_var, saved_ctxs in saved_var_contexts.items():
                            if ctx in saved_ctxs:
                                headers[header_name] = header_value.replace(
                                    f"${{{ref}}}", f"${{{saved_var}}}")
                                total_replacements += 1
                                break

            # URL 路径变量（无参数上下文，仅精确匹配已知变量）
            iface = case.get("interface") or {}
            if iface.get("url"):
                for ref in var_pattern.findall(iface["url"]):
                    if ref in all_known:
                        continue
                    # 对 URL 变量尝试参数上下文回退
                    ref_parts = set(re.split(r'[_\-]', ref.lower()))
                    for saved_var in saved_var_contexts:
                        known_parts = set(re.split(r'[_\-]', saved_var.lower()))
                        common = ref_parts & known_parts
                        meaningful = {p for p in common if len(p) >= 3}
                        if meaningful and len(meaningful) >= len(ref_parts) * 0.5:
                            iface["url"] = iface["url"].replace(
                                f"${{{ref}}}", f"${{{saved_var}}}")
                            total_replacements += 1
                            break

            # scripts 补充匹配
            for sf in ('setup_script', 'teardown_script'):
                script = case.get(sf) or ""
                for ref in var_pattern.findall(script):
                    if ref in all_known:
                        continue
                    ref_parts = set(re.split(r'[_\-]', ref.lower()))
                    for saved_var in saved_var_contexts:
                        known_parts = set(re.split(r'[_\-]', saved_var.lower()))
                        common = ref_parts & known_parts
                        meaningful = {p for p in common if len(p) >= 3}
                        if meaningful and len(meaningful) >= len(ref_parts) * 0.5:
                            script = script.replace(f"${{{ref}}}", f"${{{saved_var}}}")
                            total_replacements += 1
                            break
                case[sf] = script

    @classmethod
    async def _pre_run_selected_base_cases(
        cls,
        *,
        selected_items: list[tuple[int, dict]],
        api_doc: str,
        precoditions_api_doc: list,
        environment_id: int,
        project_id: int,
        test_env_data: dict | None = None,
        progress_callback=None,
        skip_execution: bool = False,
        language_overlay: str = "",
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

        from service.ai_engine.workflow.api_case_main_workflow import concurrent_pre_run_base_cases

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
            test_env_data=test_env_data,
            additional_info=build_default_additional_info(),
            progress_callback=progress_callback,
            skip_execution=skip_execution,
            max_workers=None,
            language_overlay=language_overlay,
        )

    @classmethod
    async def _execute_cases_async(
        cls,
        *,
        case_ids: list[int],
        environment_id: int,
        user_id: int,
    ) -> None:
        """Phase 2: 异步并发执行已保存的用例，更新 exec_status。

        使用 asyncio.Semaphore 控制并发数（MAX_BATCH_SIZE），
        所有用例同时发起执行，但最多只有 MAX_BATCH_SIZE 个在运行。
        """
        from service.api_test.models import ApiTestCase
        from service.api_test.shared.runner_gateway import RunnerGateway
        from service.core.settings import MAX_BATCH_SIZE
        from service.core.enums import ExecStatus

        logger.info("[Phase2] 开始异步并发执行 %d 个用例, max_workers=%d", len(case_ids), MAX_BATCH_SIZE)
        sem = asyncio.Semaphore(MAX_BATCH_SIZE)

        async def _run_one(case_id: int):
            async with sem:
                try:
                    record = await RunnerGateway.run_case_debug(
                        case_id=case_id,
                        environment_id=environment_id,
                        triggered_by_id=user_id,
                    )
                    if record.status == CaseRunStatus.success:
                        new_status = ExecStatus.success
                    elif record.status == CaseRunStatus.fail:
                        new_status = ExecStatus.fail
                    else:
                        new_status = ExecStatus.error
                    await ApiTestCase.filter(id=case_id).update(exec_status=new_status)
                    logger.info("[Phase2] case_id=%d 执行完成, status=%s", case_id, new_status.value)
                except Exception as exc:
                    logger.warning("[Phase2] case_id=%d 执行失败: %s", case_id, exc)
                    try:
                        await ApiTestCase.filter(id=case_id).update(exec_status=ExecStatus.error)
                    except Exception:
                        pass

        await asyncio.gather(*[_run_one(cid) for cid in case_ids])
        logger.info("[Phase2] 全部用例执行完毕, count=%d", len(case_ids))

    # ==================== v2-Q3: generation-status 轮询 ====================

    @classmethod
    async def get_generation_status(
        cls,
        user: User,
        interface_id: int,
        session_id: int,
    ) -> GenerationStatusOut:
        """v3: 查询AI预执行进度，供前端5s轮询。读取 session.output_payload 中的真实进度。"""
        session = await cls._get_api_session_or_404(session_id)
        # 验证session归属
        if (
            session.input_ref_type == InputRefType.interface
            and session.input_ref_id != interface_id
        ):
            raise AppException("生成会话与接口不匹配", 400)
        await ensure_api_viewer(session.project_id, user)

        output = session.output_payload or {}

        # 从 output_payload 中读取真实进度（由后台 _run_confirm_background 更新）
        progress = output.get("confirm_progress")
        # 如果预执行已完成，附上最终结果
        confirm_result = output.get("confirm_result")

        # 如果预览生成已完成，附上 base_cases
        base_cases_out = None
        if session.status == SessionStatus.success and "base_cases" in output:
            raw_cases = output["base_cases"]
            base_cases_out = [
                BaseCasePreviewItem(
                    index=i,
                    name=str(c.get("name") or f"用例-{i + 1}") if isinstance(c, dict) else str(c) or f"用例-{i + 1}",
                    steps=list(c.get("steps") or []) if isinstance(c, dict) else [],
                    dependencies=list(c.get("dependencies") or []) if isinstance(c, dict) else [],
                    expected=list(c.get("expected") or []) if isinstance(c, dict) else [],
                )
                for i, c in enumerate(raw_cases)
            ]

        return GenerationStatusOut(
            session_id=session.id,
            status=session.status.value if hasattr(session.status, "value") else str(session.status),
            started_at=session.created_at,
            completed_at=session.finished_at,
            progress=progress,
            error_message=session.error_message,
            confirm_result=confirm_result,
            base_cases=base_cases_out,
        )
