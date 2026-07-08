"""测试管理模块 - picker/picker_service

业务逻辑服务
"""
from tortoise.expressions import Q

from service.api_test.models import ApiTestCase
from service.core.enums import TaskSuiteType
from service.core.pagination import paginate
from service.functional_test.case.models import FunctionalCase
from service.project.models import ProjectModule
from service.test_management.models import TestSuite
from service.test_management.permissions import ensure_tm_viewer
from service.test_management.shared.case_count_query import count_suite_cases
from service.test_management.picker.schemas import (
    ApiCasePickerOut,
    ApiCasePickerQuery,
    FunctionalCasePickerOut,
    FunctionalCasePickerQuery,
    PaginatedApiCasePicker,
    PaginatedFunctionalCasePicker,
    PaginatedSuitePicker,
    SuitePickerOut,
    SuitePickerQuery,
)
from service.user.models import User


class PickerService:
    @classmethod
    async def list_api_cases(cls, user: User, query: ApiCasePickerQuery) -> PaginatedApiCasePicker:
        await ensure_tm_viewer(query.project_id, user)
        qs = ApiTestCase.filter(
            project_id=query.project_id
        ).select_related("interface").order_by("-updated_at", "-id")
        if query.q:
            kw = query.q.strip()
            qs = qs.filter(
                Q(title__icontains=kw)
                | Q(interface__summary__icontains=kw)
                | Q(interface__path__icontains=kw)
            )
        total, items = await paginate(qs, query.page, query.page_size)
        out: list[ApiCasePickerOut] = []
        for case in items:
            iface_name = iface_path = iface_method = None
            if case.interface_id and case.interface:
                iface = case.interface
                iface_name = iface.summary
                iface_path = iface.path
                iface_method = iface.method
            out.append(
                ApiCasePickerOut(
                    id=case.id,
                    title=case.title,
                    interface_id=case.interface_id,
                    interface_name=iface_name,
                    interface_path=iface_path,
                    interface_method=iface_method,
                    exec_status=case.exec_status,
                )
            )
        return PaginatedApiCasePicker(
            total=total, page=query.page, page_size=query.page_size, items=out
        )

    @classmethod
    async def list_functional_cases(
        cls, user: User, query: FunctionalCasePickerQuery
    ) -> PaginatedFunctionalCasePicker:
        await ensure_tm_viewer(query.project_id, user)
        qs = FunctionalCase.filter(project_id=query.project_id).order_by(
            "sort_order", "id"
        )
        if query.module_id is not None:
            qs = qs.filter(module_id=query.module_id)
        if query.q:
            qs = qs.filter(case_name__icontains=query.q.strip())
        total, items = await paginate(qs, query.page, query.page_size)
        module_ids = {c.module_id for c in items if c.module_id}
        modules = {}
        if module_ids:
            rows = await ProjectModule.filter(id__in=list(module_ids)).values("id", "name")
            modules = {r["id"]: r["name"] for r in rows}
        out = [
            FunctionalCasePickerOut(
                id=c.id,
                case_name=c.case_name,
                case_no=c.case_no,
                module_id=c.module_id,
                module_name=modules.get(c.module_id) if c.module_id else None,
                catalog_id=c.catalog_id,
                priority=c.priority,
                case_category=c.case_category,
            )
            for c in items
        ]
        return PaginatedFunctionalCasePicker(
            total=total, page=query.page, page_size=query.page_size, items=out
        )

    @classmethod
    async def list_suites(cls, user: User, query: SuitePickerQuery) -> PaginatedSuitePicker:
        await ensure_tm_viewer(query.project_id, user)
        qs = TestSuite.filter(project_id=query.project_id).order_by("-updated_at", "-id")
        if query.type is not None:
            qs = qs.filter(type=query.type)
        if query.q:
            qs = qs.filter(suite_name__icontains=query.q.strip())
        total, items = await paginate(qs, query.page, query.page_size)
        suite_ids = [s.id for s in items]
        counts = await count_suite_cases(suite_ids)
        out = [
            SuitePickerOut(
                id=s.id,
                suite_name=s.suite_name,
                type=s.type,
                case_count=counts.get(s.id, 0),
            )
            for s in items
        ]
        return PaginatedSuitePicker(
            total=total, page=query.page, page_size=query.page_size, items=out
        )
