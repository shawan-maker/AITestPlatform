from service.api_test.case.schemas import (
    CaseBatchDeleteRequest,
    CaseOut,
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
from service.core.enums import ApiCaseKind
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
        qs = ApiTestCase.filter(interface_id=iface.id)
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
                interface_id=case.interface_id, title=data.title
            ).exclude(id=case.id).exists()
            if exists:
                raise AppException("同接口下用例标题已存在", 409)
            case.title = data.title
        if data.case_payload is not None:
            case.case_payload = data.case_payload
        case.updated_by_id = user.id
        await case.save()
        return cls._to_out(case)

    @classmethod
    async def delete(cls, user: User, case_id: int) -> None:
        case = await cls._get_case_or_404(case_id)
        await ensure_api_editor(case.project_id, user)
        await remove_suite_relations_for_cases([case.id])
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
        await remove_suite_relations_for_cases(data.case_ids)
        await ApiTestCase.filter(id__in=data.case_ids).delete()

    @classmethod
    async def debug_run(
        cls, user: User, case_id: int, *, environment_id: int
    ):
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
        return RunRecordOut(
            id=record.id,
            case_name=record.case_name,
            status=record.status.value,
            run_type=record.run_type.value,
            duration_ms=record.duration_ms,
            error_message=record.error_message,
            created_at=record.created_at,
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
        qs = ApiCaseRunRecord.filter(api_case_id=case.id).order_by("-created_at")
        total, items = await paginate(qs, page, page_size)
        return PaginatedRunRecords(
            total=total,
            page=page,
            page_size=page_size,
            items=[
                RunRecordOut(
                    id=r.id,
                    case_name=r.case_name,
                    status=r.status.value,
                    run_type=r.run_type.value,
                    duration_ms=r.duration_ms,
                    error_message=r.error_message,
                    created_at=r.created_at,
                )
                for r in items
            ],
        )
