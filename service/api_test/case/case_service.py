"""接口测试模块 - case/case_service

业务逻辑服务
"""
from service.api_test.case.schemas import (
    CaseBatchDeleteRequest,
    CaseOut,
    CaseReuseRequest,
    CaseReuseResult,
    CaseUpdateRequest,
    PaginatedCases,
    PaginatedRunRecords,
    RunRecordOut,
)
from service.api_test.interface.interface_service import InterfaceService
from service.api_test.models import ApiTestCase
from service.api_test.permissions import ensure_api_editor, ensure_api_viewer
from service.api_test.shared.runner_gateway import RunnerGateway
from service.api_test.shared.suite_guard import remove_suite_relations_for_cases
from service.core.enums import ApiCaseKind, ExecStatus, ReviewStatus
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.test_environment.models import TestEnvironment
from service.test_execution.models import ApiCaseRunRecord
from service.user.models import User


class CaseService:
    @classmethod
    async def _get_case_or_404(cls, case_id: int) -> ApiTestCase:
        # v2-L5: 并发删除时返回友好提示
        case = await ApiTestCase.get_or_none(id=case_id)
        if case is None:
            raise AppException("该用例已被删除，请刷新页面", 404)
        return case

    @classmethod
    def _to_out(cls, case: ApiTestCase) -> CaseOut:
        updated_by_name = None
        try:
            if case.updated_by:
                updated_by_name = case.updated_by.username
        except Exception:
            pass
        return CaseOut(
            id=case.id,
            project_id=case.project_id,
            interface_id=case.interface_id,
            title=case.title,
            case_kind=case.case_kind,
            sort_order=case.sort_order,
            case_payload=case.case_payload,
            review_status=case.review_status,
            exec_status=case.exec_status,
            generation_count=case.generation_count,
            default_file_id=case.default_file_id,
            updated_by_name=updated_by_name,
            last_run_at=case.last_run_at,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    @classmethod
    async def list_by_interface(
        cls,
        user: User,
        interface_id: int,
        *,
        case_kind: ApiCaseKind | None,
        page: int,
        page_size: int,
    ) -> PaginatedCases:
        iface = await InterfaceService._get_current_or_404(interface_id)
        await ensure_api_viewer(iface.project_id, user)
        qs = ApiTestCase.filter(interface_id=iface.id).prefetch_related("updated_by")
        if case_kind is not None:
            qs = qs.filter(case_kind=case_kind)
        qs = qs.order_by("sort_order", "id")
        total, items = await paginate(qs, page, page_size)
        return PaginatedCases(
            total=total,
            page=page,
            page_size=page_size,
            items=[cls._to_out(c) for c in items],
        )

    @classmethod
    async def get_detail(cls, user: User, case_id: int) -> CaseOut:
        case = await cls._get_case_or_404(case_id)
        await ensure_api_viewer(case.project_id, user)
        return cls._to_out(case)

    @classmethod
    async def update(
        cls, user: User, case_id: int, data: CaseUpdateRequest
    ) -> CaseOut:
        case = await cls._get_case_or_404(case_id)
        await ensure_api_editor(case.project_id, user)
        if data.title is not None:
            exists = await ApiTestCase.filter(
                interface_id=case.interface_id,
                case_kind=case.case_kind,
                title=data.title,
            ).exclude(id=case.id).exists()
            if exists:
                raise AppException("同接口同类型下用例标题已存在", 409)
            case.title = data.title
        if data.case_payload is not None:
            # 保留后端生成的关键字段，避免前端编辑时误覆盖
            old = case.case_payload or {}
            new = data.case_payload
            if isinstance(old, dict) and isinstance(new, dict):
                for key in ("precondition_ids", "preconditions"):
                    if key in old and key not in new:
                        new[key] = old[key]
            case.case_payload = new
        case.updated_by_id = user.id
        await case.save()
        return cls._to_out(case)

    @classmethod
    async def batch_get(cls, user: User, case_ids: list[int]) -> list[CaseOut]:
        """Fetch cases by a list of IDs (cross-interface)."""
        if not case_ids:
            return []
        qs = ApiTestCase.filter(id__in=case_ids).prefetch_related("updated_by").order_by("sort_order", "id")
        items = await qs.limit(200)
        if items:
            await ensure_api_viewer(items[0].project_id, user)
        return [cls._to_out(c) for c in items]

    @classmethod
    async def unlink_precondition(cls, user: User, case_id: int, pre_id: int) -> None:
        """从主用例的 precondition_ids 中移除指定前置用例 ID（解除关联，不删除前置用例本身）。"""
        case = await cls._get_case_or_404(case_id)
        await ensure_api_editor(case.project_id, user)
        payload = case.case_payload or {}
        pre_ids = payload.get("precondition_ids") or []
        if pre_id not in pre_ids:
            raise AppException("该前置用例未被此主用例关联", 400)
        pre_ids = [pid for pid in pre_ids if pid != pre_id]
        payload["precondition_ids"] = pre_ids
        case.case_payload = payload
        case.updated_by_id = user.id
        await case.save(update_fields=["case_payload", "updated_by_id", "updated_at"])

    @classmethod
    async def delete(cls, user: User, case_id: int) -> None:
        case = await cls._get_case_or_404(case_id)
        await ensure_api_editor(case.project_id, user)
        # 删除前置用例前检查是否有主用例引用
        if case.case_kind == ApiCaseKind.precondition:
            main_cases = await ApiTestCase.filter(
                case_kind=ApiCaseKind.main,
            ).all()
            referencing_titles = []
            for mc in main_cases:
                pre_ids = (mc.case_payload or {}).get("precondition_ids") or []
                if case.id in pre_ids:
                    referencing_titles.append(mc.title)
            if referencing_titles:
                names = ", ".join(referencing_titles[:3])
                suffix = f" 等{len(referencing_titles)}个" if len(referencing_titles) > 3 else ""
                raise AppException(
                    f"该前置用例被以下主用例引用，请先解除关联：{names}{suffix}",
                    409,
                )
        await remove_suite_relations_for_cases([case.id])
        await ApiCaseRunRecord.filter(api_case_id=case.id).delete()
        await case.delete()

    @classmethod
    async def batch_delete(cls, user: User, data: CaseBatchDeleteRequest) -> None:
        cases = await ApiTestCase.filter(id__in=data.case_ids)
        if not cases:
            raise AppException("用例不存在", 404)
        project_ids = {c.project_id for c in cases}
        if len(project_ids) != 1:
            raise AppException("批量删除的用例须属于同一项目", 400)
        project_id = next(iter(project_ids))
        await ensure_api_editor(project_id, user)
        # 检查前置用例是否被主用例引用
        pre_cases = [c for c in cases if c.case_kind == ApiCaseKind.precondition]
        if pre_cases:
            pre_ids_set = {c.id for c in pre_cases}
            main_cases = await ApiTestCase.filter(case_kind=ApiCaseKind.main).all()
            blocked = []
            for mc in main_cases:
                mc_pre_ids = (mc.case_payload or {}).get("precondition_ids") or []
                for pid in mc_pre_ids:
                    if pid in pre_ids_set:
                        blocked.append(mc.title)
                        break
            if blocked:
                names = ", ".join(blocked[:3])
                suffix = f" 等{len(blocked)}个" if len(blocked) > 3 else ""
                raise AppException(
                    f"部分前置用例被以下主用例引用，请先解除关联：{names}{suffix}",
                    409,
                )
        await remove_suite_relations_for_cases(data.case_ids)
        await ApiCaseRunRecord.filter(api_case_id__in=data.case_ids).delete()
        await ApiTestCase.filter(id__in=data.case_ids).delete()

    @staticmethod
    async def _next_case_sort_order(interface_id: int, case_kind) -> int:
        last = (
            await ApiTestCase.filter(interface_id=interface_id, case_kind=case_kind)
            .order_by("-sort_order")
            .first()
        )
        return (last.sort_order + 1) if last else 0

    @classmethod
    async def reuse(cls, user: User, data: CaseReuseRequest) -> CaseReuseResult:
        """将源用例复制到目标接口下，case_kind 由调用方指定。"""
        source_cases = await ApiTestCase.filter(id__in=data.source_case_ids)
        if not source_cases:
            raise AppException("源用例不存在", 404)

        target_iface = await InterfaceService._get_current_or_404(data.target_interface_id)
        await ensure_api_editor(target_iface.project_id, user)

        sort_base = await cls._next_case_sort_order(target_iface.id, data.target_case_kind)
        created_ids: list[int] = []
        failures: list[dict] = []

        for order, src in enumerate(source_cases):
            try:
                title = src.title
                # 唯一约束 (interface_id, case_kind, title)：同接口不同 case_kind 可同名
                exists = await ApiTestCase.filter(
                    interface_id=target_iface.id,
                    case_kind=data.target_case_kind,
                    title=title,
                ).exclude(id=src.id).exists()
                if exists:
                    base = title
                    suffix_idx = 1
                    while True:
                        candidate = f"{base}_reuse{suffix_idx:02d}"
                        dup = await ApiTestCase.filter(
                            interface_id=target_iface.id,
                            case_kind=data.target_case_kind,
                            title=candidate,
                        ).exists()
                        if not dup:
                            title = candidate
                            break
                        suffix_idx += 1

                new_case = await ApiTestCase.create(
                    project_id=target_iface.project_id,
                    module_id=target_iface.module_id,
                    interface_id=target_iface.id,
                    title=title,
                    case_kind=data.target_case_kind,
                    sort_order=sort_base + order,
                    case_payload=src.case_payload,
                    review_status=ReviewStatus.init,
                    exec_status=ExecStatus.pending,
                    created_by_id=user.id,
                    updated_by_id=user.id,
                )
                created_ids.append(new_case.id)
            except Exception as e:
                failures.append({"case_id": src.id, "message": str(e)})

        return CaseReuseResult(
            created_count=len(created_ids),
            created_ids=created_ids,
            failures=failures,
        )

    @classmethod
    async def list_by_interfaces(
        cls, user: User, interface_ids: list[int]
    ) -> list[CaseOut]:
        """按接口ID批量查询用例（不分页，最多200条）。"""
        if not interface_ids:
            return []
        qs = (
            ApiTestCase.filter(interface_id__in=interface_ids)
            .prefetch_related("updated_by")
            .order_by("interface_id", "sort_order", "id")
        )
        items = await qs.limit(200)
        # 权限校验：取第一个用例的 project_id 验证
        if items:
            await ensure_api_viewer(items[0].project_id, user)
        return [cls._to_out(c) for c in items]

    @classmethod
    async def trigger_debug_run(
        cls, user: User, case_id: int, *, environment_id: int
    ) -> dict:
        """创建 running 状态的运行记录，然后异步执行。立即返回 record_id。"""
        import asyncio

        case = await cls._get_case_or_404(case_id)
        await ensure_api_editor(case.project_id, user)
        env = await TestEnvironment.get_or_none(
            id=environment_id, project_id=case.project_id
        )
        if env is None:
            raise AppException("测试环境不存在", 404)

        # 创建 running 状态的记录
        from datetime import datetime, timezone
        from service.core.enums import CaseRunStatus, CaseRunType
        from service.test_execution.models import ApiCaseRunRecord

        record = await ApiCaseRunRecord.create(
            api_case_id=case.id,
            interface_id=case.interface_id,
            run_type=CaseRunType.debug,
            environment_id=environment_id,
            triggered_by_id=user.id,
            case_name=case.title,
            status=CaseRunStatus.running,
            start_time=datetime.now(timezone.utc),
        )
        # 更新用例执行状态为 running
        from service.core.enums import ExecStatus
        case.exec_status = ExecStatus.running
        await case.save(update_fields=["exec_status", "updated_at"])

        # 同时更新关联的前置用例状态为 running
        pre_ids = (case.case_payload or {}).get("precondition_ids") or []
        if pre_ids:
            await ApiTestCase.filter(id__in=pre_ids).update(exec_status=ExecStatus.running)

        # 异步执行（不阻塞 HTTP 响应）
        asyncio.create_task(
            cls._execute_debug_run_background(
                record_id=record.id,
                case_id=case.id,
                environment_id=environment_id,
                triggered_by_id=user.id,
            )
        )
        return {"record_id": record.id, "status": "running"}

    @classmethod
    async def _execute_debug_run_background(
        cls, *, record_id: int, case_id: int, environment_id: int, triggered_by_id: int
    ) -> None:
        """后台执行调试运行，完成后更新记录。"""
        import logging
        logger = logging.getLogger(__name__)
        try:
            await RunnerGateway.run_case_debug(
                case_id=case_id,
                environment_id=environment_id,
                triggered_by_id=triggered_by_id,
                existing_record_id=record_id,
            )
        except Exception as e:
            logger.exception("Debug run background error: record_id=%s", record_id)
            # 更新记录为 error 状态
            from service.core.enums import CaseRunStatus
            from service.test_execution.models import ApiCaseRunRecord
            from datetime import datetime, timezone
            try:
                record = await ApiCaseRunRecord.get_or_none(id=record_id)
                if record:
                    record.status = CaseRunStatus.error
                    record.error_message = str(e)
                    record.end_time = datetime.now(timezone.utc)
                    if record.start_time:
                        record.duration_ms = int((record.end_time - record.start_time).total_seconds() * 1000)
                    await record.save()
            except Exception:
                logger.exception("Failed to update error status for record_id=%s", record_id)

    @classmethod
    async def get_debug_run_status(
        cls, user: User, case_id: int, record_id: int
    ) -> RunRecordOut:
        """轮询调试运行状态。"""
        case = await cls._get_case_or_404(case_id)
        await ensure_api_viewer(case.project_id, user)
        from service.test_execution.models import ApiCaseRunRecord
        record = await ApiCaseRunRecord.get_or_none(id=record_id, api_case_id=case_id)
        if record is None:
            raise AppException("运行记录不存在", 404)

        detail = None
        if record.api_requests_info and isinstance(record.api_requests_info, dict):
            detail = record.api_requests_info.get("_debug_detail") or record.api_requests_info

        iface_name = None
        if record.interface_id:
            from service.api_test.interface.interface_service import InterfaceService
            try:
                iface = await InterfaceService._get_current_or_404(record.interface_id)
                iface_name = iface.summary or iface.name
            except Exception:
                pass

        triggered_name = None
        if record.triggered_by_id:
            from service.user.models import User as UserModel
            u = await UserModel.get_or_none(id=record.triggered_by_id)
            triggered_name = u.username if u else None

        return RunRecordOut(
            id=record.id,
            case_name=record.case_name,
            interface_name=iface_name,
            status=record.status.value,
            run_type=record.run_type.value,
            duration_ms=record.duration_ms,
            error_message=record.error_message,
            created_at=record.created_at,
            triggered_by_username=triggered_name,
            api_requests_info=detail,
        )

    @classmethod
    async def debug_run(
        cls, user: User, case_id: int, *, environment_id: int
    ):
        """保留同步版本供内部调用（兼容）。"""
        case = await cls._get_case_or_404(case_id)
        await ensure_api_editor(case.project_id, user)
        env = await TestEnvironment.get_or_none(
            id=environment_id, project_id=case.project_id
        )
        if env is None:
            raise AppException("测试环境不存在", 404)
        record = await RunnerGateway.run_case_debug(
            case=case,
            environment_id=environment_id,
            triggered_by_id=user.id,
        )
        # 提取详细执行结果
        detail = None
        if record.api_requests_info and isinstance(record.api_requests_info, dict):
            detail = record.api_requests_info.get("_debug_detail") or record.api_requests_info
        # 获取接口名称
        iface_name = None
        if record.interface_id:
            from service.api_test.interface.interface_service import InterfaceService
            try:
                iface = await InterfaceService._get_current_or_404(record.interface_id)
                iface_name = iface.summary or iface.name
            except Exception:
                pass
        return RunRecordOut(
            id=record.id,
            case_name=record.case_name,
            interface_name=iface_name,
            status=record.status.value,
            run_type=record.run_type.value,
            duration_ms=record.duration_ms,
            error_message=record.error_message,
            created_at=record.created_at,
            triggered_by_username=user.username,
            api_requests_info=detail,
        )

    @classmethod
    async def list_run_records(
        cls,
        user: User,
        case_id: int,
        *,
        page: int,
        page_size: int,
    ) -> PaginatedRunRecords:
        case = await cls._get_case_or_404(case_id)
        await ensure_api_viewer(case.project_id, user)
        qs = ApiCaseRunRecord.filter(api_case_id=case.id).order_by("-created_at").prefetch_related("interface", "triggered_by")
        total, items = await paginate(qs, page, page_size)
        return PaginatedRunRecords(
            total=total,
            page=page,
            page_size=page_size,
            items=[
                RunRecordOut(
                    id=r.id,
                    case_name=r.case_name,
                    interface_name=r.interface.summary if r.interface else None,
                    status=r.status.value,
                    run_type=r.run_type.value,
                    duration_ms=r.duration_ms,
                    error_message=r.error_message,
                    created_at=r.created_at,
                    triggered_by_username=r.triggered_by.username if r.triggered_by else None,
                    api_requests_info=r.api_requests_info,
                )
                for r in items
            ],
        )
