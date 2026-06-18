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
    index: int
    api_case: dict
    review_status: ReviewStatus
    error: str | None = None


class ApiCaseGenerationService:
    # 防止后台任务被 GC 回收
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
        await session.save(update_fields=["status", "output_payload"])

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

            # 未选择环境：跳过预执行，直接创建 DB 记录，状态为 pending
            if not environment_id:
                logger.info("[预执行] session=%s 未选择环境，跳过预执行，直接保存", session.id)
                # 创建 precondition 用例
                precondition_map = await cls._create_precondition_cases(
                    interface=iface,
                    base_cases=base_cases,
                    selected_indexes=[idx for idx, _ in selected_items],
                    precoditions_api_doc=precoditions_api_doc,
                    environment_id=None,
                    test_env_data=None,
                    user_id=user.id,
                    session_id=session.id,
                )
                async with in_transaction():
                    sort_base = await cls._next_case_sort_order(iface.id, ApiCaseKind.main)
                    for order, (idx, base) in enumerate(selected_items):
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
                            title=str(base.get("name") or base_row.name),
                            case_kind=ApiCaseKind.main,
                            sort_order=sort_base + order,
                            case_payload={
                                "title": base.get("name", ""),
                                "method": getattr(iface, "method", "GET"),
                                "path": getattr(iface, "path", ""),
                                "headers": {},
                                "query": {},
                                "body": None,
                                "assertions": [
                                    {"target": exp, "method": "contains", "expected": ""}
                                    for exp in (base.get("expected") or [])
                                ],
                                "steps": base.get("steps") or [],
                                "expected": base.get("expected") or [],
                                "preconditions": [],
                                "precondition_ids": [
                                    precondition_map[cls._clean_dependency_name(str(d).strip())]
                                    for d in (base.get("dependencies") or [])
                                    if cls._clean_dependency_name(str(d).strip()) in precondition_map
                                ] if precondition_map else [],
                            },
                            review_status=ReviewStatus.init,
                            exec_status=ExecStatus.pending,
                            environment_id=None,
                            generation_session_id=session.id,
                            created_by_id=user.id,
                            updated_by_id=user.id,
                        )
                        created_case_ids.append(case_row.id)

                session.output_payload["confirm_result"] = {
                    "created_base_case_ids": created_base_ids,
                    "created_case_ids": created_case_ids,
                    "run_errors": [],
                    "created_interface_id": created_interface_id,
                    "created_precondition_ids": list(precondition_map.values()) if precondition_map else [],
                }
                session.output_payload["confirm_progress"]["completed"] = len(selected_items)
                session.status = SessionStatus.success
                session.finished_at = datetime.now(timezone.utc)
                await session.save(update_fields=["status", "output_payload", "finished_at"])
                logger.info("[预执行] session=%s 直接保存完成, cases=%d", session.id, len(created_case_ids))
                return

            # 选择了环境：执行预执行流程
            from service.test_execution.env_loader import load_test_env_data
            test_env_data = await load_test_env_data(environment_id)
            logger.info("[预执行] session=%s 环境数据加载完成", session.id)

            # 定义进度回调 — 在线程中执行，通过 run_coroutine_threadsafe 持久化到 DB
            loop = asyncio.get_running_loop()

            def on_progress(completed, total, item):
                progress = session.output_payload.get("confirm_progress", {})
                progress["completed"] = completed
                progress["stage"] = "executing"
                for pi in progress.get("items", []):
                    if pi.get("index") == item.get("index"):
                        pi["status"] = item.get("status", "pending")
                        pi["error"] = item.get("error")
                session.output_payload["confirm_progress"] = progress
                # 异步持久化进度到 DB（不阻塞线程）
                try:
                    asyncio.run_coroutine_threadsafe(
                        session.save(update_fields=["output_payload"]),
                        loop,
                    )
                except Exception:
                    pass  # 持久化失败不影响执行

            # 当正式依赖文档为空时，从 DB 按 base_case dependencies 名称查找接口文档
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
                    logger.info(
                        "[预执行] precoditions_api_doc 原为空, 从 DB 补充 %d 个接口文档",
                        len(precoditions_api_doc),
                    )

            pre_run_results = await cls._pre_run_selected_base_cases(
                selected_items=selected_items,
                api_doc=api_doc,
                precoditions_api_doc=precoditions_api_doc,
                environment_id=environment_id,
                project_id=iface.project_id,
                test_env_data=test_env_data,
                progress_callback=on_progress,
            )

            logger.info(
                "[预执行] session=%s 预执行完成, results=%d",
                session.id, len(pre_run_results),
            )
            for r in pre_run_results:
                logger.info(
                    "[预执行]   case[%d] review=%s error=%s",
                    r.index, r.review_status, r.error,
                )
                logger.info(
                    "[预执行]   case[%d] api_case keys=%s",
                    r.index, list(r.api_case.keys()) if isinstance(r.api_case, dict) else type(r.api_case),
                )

            # 收集 AI 生成的前置步骤（按 title 去重）
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
            if ai_precondition_map:
                logger.info(
                    "[预执行] 收集到 %d 个 AI 前置步骤: %s",
                    len(ai_precondition_map), list(ai_precondition_map.keys()),
                )

            # 创建 precondition 用例（优先使用 AI 数据）
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

            # 从 workflow 预执行结果中提取前置步骤独立执行数据，更新 DB 前置用例
            if precondition_map:
                await cls._update_precondition_results_from_pre_run(
                    precondition_map, pre_run_results,
                )

            # 创建 DB 记录
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

                    # 构建主用例 payload；DB 前置用例已创建时移除 AI 内嵌前置步骤
                    main_exec_result = dict(pre_result.exec_result or {})
                    main_payload = {
                        **pre_result.api_case,
                        "_exec_result": main_exec_result,
                    }
                    if precondition_map:
                        main_payload["preconditions"] = []
                        # 记录该主用例关联的前置用例 ID
                        dep_names = [cls._clean_dependency_name(str(d).strip()) for d in (base.get("dependencies") or [])]
                        main_payload["precondition_ids"] = [
                            precondition_map[n] for n in dep_names if n in precondition_map
                        ]

                    case_row = await ApiTestCase.create(
                        project_id=iface.project_id,
                        module_id=iface.module_id,
                        base_case_id=base_row.id,
                        interface_id=iface.id,
                        title=str(pre_result.api_case.get("title") or base_row.name),
                        case_kind=ApiCaseKind.main,
                        sort_order=sort_base + order,
                        case_payload=main_payload,
                        review_status=pre_result.review_status,
                        exec_status=ExecStatus.success
                        if pre_result.review_status == ReviewStatus.success
                        else ExecStatus.fail
                        if pre_result.review_status == ReviewStatus.fail
                        else ExecStatus.error
                        if pre_result.review_status == ReviewStatus.error
                        else ExecStatus.pending,
                        environment_id=environment_id,
                        generation_session_id=session.id,
                        created_by_id=user.id,
                        updated_by_id=user.id,
                    )
                    created_case_ids.append(case_row.id)

            # 为预执行创建测试记录
            from service.test_execution.models import ApiCaseRunRecord
            from datetime import datetime as _dt

            # 为主用例创建测试记录
            for order, pre_result in enumerate(pre_run_results):
                if order >= len(created_case_ids):
                    break
                case_id = created_case_ids[order]
                er = pre_result.exec_result or {}
                if isinstance(er, dict) and "cases" in er:
                    cases_list = er.get("cases") or []
                    er = cases_list[0] if cases_list else {}

                review = pre_result.review_status
                run_status = (
                    CaseRunStatus.success if review == ReviewStatus.success
                    else CaseRunStatus.fail if review == ReviewStatus.fail
                    else CaseRunStatus.error
                )
                case_title = ""
                if isinstance(pre_result.api_case, dict):
                    case_title = pre_result.api_case.get("title", "")

                try:
                    await ApiCaseRunRecord.create(
                        api_case_id=case_id,
                        interface_id=iface.id,
                        run_type=CaseRunType.debug,
                        environment_id=environment_id,
                        triggered_by_id=user.id,
                        case_name=case_title or f"用例-{case_id}",
                        status=run_status,
                        case_snapshot=pre_result.api_case if isinstance(pre_result.api_case, dict) else None,
                        error_message=pre_result.error,
                        start_time=_dt.now(timezone.utc),
                        end_time=_dt.now(timezone.utc),
                        duration_ms=0,
                        api_requests_info=er if isinstance(er, dict) else None,
                    )
                except Exception as exc:
                    logger.warning("[预执行] 创建主用例测试记录失败 case_id=%s: %s", case_id, exc)

            # 为前置操作用例创建测试记录
            if precondition_map:
                # 从预执行结果中收集 per-step 数据
                pre_step_data_all: dict[str, dict] = {}
                for pre_result in pre_run_results:
                    er = pre_result.exec_result or {}
                    if isinstance(er, dict) and "cases" in er:
                        cases_list = er.get("cases") or []
                        er = cases_list[0] if cases_list else {}
                    if isinstance(er, dict):
                        for ps in (er.get("precondition_results") or []):
                            t = (ps.get("title") or "").strip()
                            if t:
                                pre_step_data_all[t] = ps

                for dep_name, pre_id in precondition_map.items():
                    step = pre_step_data_all.get(dep_name, {})
                    sc = step.get("status_code", "")
                    pre_status = (
                        CaseRunStatus.success if str(sc).startswith("2")
                        else CaseRunStatus.fail if sc
                        else CaseRunStatus.error
                    )
                    try:
                        await ApiCaseRunRecord.create(
                            api_case_id=pre_id,
                            interface_id=iface.id,
                            run_type=CaseRunType.debug,
                            environment_id=environment_id,
                            triggered_by_id=user.id,
                            case_name=dep_name,
                            status=pre_status,
                            case_snapshot=step or None,
                            start_time=_dt.now(timezone.utc),
                            end_time=_dt.now(timezone.utc),
                            duration_ms=0,
                            api_requests_info=step if step else None,
                        )
                    except Exception as exc:
                        logger.warning("[预执行] 创建前置用例测试记录失败 pre_id=%s: %s", pre_id, exc)

            # 更新 session 为完成状态
            session.output_payload["confirm_result"] = {
                "created_base_case_ids": created_base_ids,
                "created_case_ids": created_case_ids,
                "run_errors": run_errors,
                "created_interface_id": created_interface_id,
                "created_precondition_ids": list(precondition_map.values()) if precondition_map else [],
            }
            session.output_payload["confirm_progress"]["completed"] = len(selected_items)
            session.status = SessionStatus.success
            session.finished_at = datetime.now(timezone.utc)
            await session.save(update_fields=["status", "output_payload", "finished_at"])
            logger.info(
                "[预执行] session=%s 完成, created_cases=%d, errors=%d",
                session.id, len(created_case_ids), len(run_errors),
            )

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
    def _build_precondition_payload(dep_name: str, dep_doc: dict) -> dict:
        """从依赖接口文档构建 precondition 用例的基础 payload。
        根据 requestBody.content_type 正确选择 request.data / request.json。
        """
        method = (dep_doc.get("method") or "GET").upper()
        path = dep_doc.get("path") or ""
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
            payload["request"]["params"] = query_params

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

        # 根据 content_type 放入正确的 request key
        if body_fields:
            if "form-urlencoded" in content_type or "multipart" in content_type:
                payload["headers"]["Content-Type"] = content_type or "application/x-www-form-urlencoded"
                payload["request"]["data"] = body_fields
            else:
                # 默认 JSON
                ct = content_type if "json" in content_type else "application/json"
                payload["headers"]["Content-Type"] = ct
                payload["request"]["json"] = body_fields

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
            if ai_step:
                from service.api_test.shared.payload_builder import _convert_precondition
                case_payload = _convert_precondition(ai_step)
                case_payload["title"] = dep_name
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
                title=dep_name,
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
        test_env_data: dict | None = None,
        progress_callback=None,
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
            test_env_data=test_env_data,
            additional_info=build_default_additional_info(),
            progress_callback=progress_callback,
        )

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
                    name=str(c.get("name") or f"用例-{i + 1}"),
                    steps=list(c.get("steps") or []),
                    dependencies=list(c.get("dependencies") or []),
                    expected=list(c.get("expected") or []),
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
