"""测试管理模块 - suite/case_relation_service

业务逻辑服务
"""
from __future__ import annotations

from tortoise.expressions import Q

from service.api_test.models import ApiTestCase
from service.api_test.interface.models import ApiInterface
from service.core.enums import ExecStatus, SuiteCaseType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.test_management.models import SuiteCaseRelation, TestSuite
from service.test_management.permissions import ensure_tm_editor, ensure_tm_viewer
from service.test_management.shared.relation_ops import replace_relations
from service.test_management.suite.schemas import (
    PaginatedSuiteCases,
    SuiteCaseAddRequest,
    SuiteCaseBatchRemoveRequest,
    SuiteCaseDependencyPatchRequest,
    SuiteCaseItemIn,
    SuiteCaseRelationOut,
    SuiteCaseReplaceRequest,
)
from service.user.models import User


class CaseRelationService:
    @classmethod
    async def _get_suite_or_404(cls, suite_id: int) -> TestSuite:
        suite = await TestSuite.get_or_none(id=suite_id)
        if suite is None:
            raise AppException("套件不存在", 404)
        return suite

    @classmethod
    async def _validate_case_ids(cls, project_id: int, case_ids: list[int]) -> None:
        if not case_ids:
            return
        count = await ApiTestCase.filter(
            id__in=case_ids, project_id=project_id
        ).count()
        if count != len(set(case_ids)):
            raise AppException("部分 API 用例不存在或不属于当前项目", 400)

    @classmethod
    async def _build_case_out(cls, rel: SuiteCaseRelation) -> SuiteCaseRelationOut:
        case = await ApiTestCase.get_or_none(id=rel.case_id)
        interface_id = interface_name = interface_path = interface_method = None
        exec_status = None
        case_name = None
        if case:
            case_name = case.title
            exec_status = case.exec_status.value if case.exec_status else None
            interface_id = case.interface_id
            if case.interface_id:
                iface = await case.interface
                if iface:
                    interface_name = iface.summary
                    interface_path = iface.path
                    interface_method = iface.method
        return SuiteCaseRelationOut(
            id=rel.id,
            case_id=rel.case_id,
            case_order=rel.case_order,
            use_dependency=rel.use_dependency,
            case_name=case_name,
            interface_id=interface_id,
            interface_name=interface_name,
            interface_path=interface_path,
            interface_method=interface_method,
            exec_status=exec_status,
        )

    @classmethod
    async def list(
        cls, user: User, suite_id: int, *, q: str | None = None, page: int = 1, page_size: int = 20
    ) -> PaginatedSuiteCases:
        suite = await cls._get_suite_or_404(suite_id)
        await ensure_tm_viewer(suite.project_id, user)
        qs = SuiteCaseRelation.filter(
            suite_id=suite_id, case_type=SuiteCaseType.api
        ).order_by("case_order", "id")
        if q:
            kw = q.strip()
            # 按用例名称或接口名称搜索
            iface_ids = await ApiInterface.filter(
                project_id=suite.project_id, summary__icontains=kw
            ).values_list("id", flat=True)
            case_ids = await ApiTestCase.filter(
                project_id=suite.project_id
            ).filter(
                Q(title__icontains=kw) | Q(interface_id__in=list(iface_ids))
            ).values_list("id", flat=True)
            qs = qs.filter(case_id__in=list(case_ids) or [-1])
        total, items = await paginate(qs, page, page_size)
        out = [await cls._build_case_out(rel) for rel in items]
        return PaginatedSuiteCases(total=total, page=page, page_size=page_size, items=out)

    @classmethod
    async def replace(
        cls,
        user: User,
        suite_id: int,
        cases: list[SuiteCaseItemIn] | SuiteCaseReplaceRequest,
        *,
        skip_permission: bool = False,
    ) -> None:
        suite = await cls._get_suite_or_404(suite_id)
        if not skip_permission:
            await ensure_tm_editor(suite.project_id, user)
        case_items = cases.cases if isinstance(cases, SuiteCaseReplaceRequest) else cases
        case_ids = [c.case_id for c in case_items]
        await cls._validate_case_ids(suite.project_id, case_ids)
        items = [
            {
                "suite_id": suite_id,
                "case_type": SuiteCaseType.api,
                "case_id": c.case_id,
                "use_dependency": c.use_dependency,
            }
            for c in case_items
        ]
        await replace_relations(SuiteCaseRelation, "suite_id", suite_id, items)

    @classmethod
    async def add(cls, user: User, suite_id: int, data: SuiteCaseAddRequest) -> None:
        suite = await cls._get_suite_or_404(suite_id)
        await ensure_tm_editor(suite.project_id, user)
        case_ids = [c.case_id for c in data.cases]
        await cls._validate_case_ids(suite.project_id, case_ids)
        max_order = (
            await SuiteCaseRelation.filter(suite_id=suite_id)
            .order_by("-case_order")
            .first()
        )
        start = (max_order.case_order if max_order else 0) + 1
        for idx, item in enumerate(data.cases):
            exists = await SuiteCaseRelation.filter(
                suite_id=suite_id,
                case_type=SuiteCaseType.api,
                case_id=item.case_id,
            ).exists()
            if exists:
                raise AppException(f"用例 {item.case_id} 已关联", 409)
            await SuiteCaseRelation.create(
                suite_id=suite_id,
                case_type=SuiteCaseType.api,
                case_id=item.case_id,
                case_order=start + idx,
                use_dependency=item.use_dependency,
            )

    @classmethod
    async def batch_remove(
        cls, user: User, suite_id: int, data: SuiteCaseBatchRemoveRequest
    ) -> None:
        suite = await cls._get_suite_or_404(suite_id)
        await ensure_tm_editor(suite.project_id, user)
        await SuiteCaseRelation.filter(
            suite_id=suite_id,
            case_type=SuiteCaseType.api,
            case_id__in=data.case_ids,
        ).delete()

    @classmethod
    async def patch_dependency(
        cls, user: User, suite_id: int, data: SuiteCaseDependencyPatchRequest
    ) -> None:
        suite = await cls._get_suite_or_404(suite_id)
        await ensure_tm_editor(suite.project_id, user)
        await SuiteCaseRelation.filter(
            suite_id=suite_id,
            case_type=SuiteCaseType.api,
            case_id__in=data.case_ids,
        ).update(use_dependency=data.use_dependency)

    @classmethod
    async def reorder(cls, user: User, suite_id: int, ordered_case_ids: list[int]) -> None:
        suite = await cls._get_suite_or_404(suite_id)
        await ensure_tm_editor(suite.project_id, user)
        relations = await SuiteCaseRelation.filter(
            suite_id=suite_id, case_type=SuiteCaseType.api
        ).all()
        rel_by_case = {r.case_id: r for r in relations}
        if set(rel_by_case.keys()) != set(ordered_case_ids):
            raise AppException("排序用例与现有关联不匹配", 400)
        for idx, case_id in enumerate(ordered_case_ids, start=1):
            rel = rel_by_case[case_id]
            rel.case_order = idx
            await rel.save(update_fields=["case_order"])
