import re

from service.core.enums import FunctionalExecResult, SourceType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.functional_test.case.catalog_service import CatalogService
from service.functional_test.case.models import FunctionalCase, FunctionalCaseCatalog, FunctionalTestPoint
from service.functional_test.permissions import ensure_case_editor, ensure_case_viewer
from service.functional_test.case.schemas import (
    BatchOperationFailure,
    CaseBatchDeleteRequest,
    CaseBatchResult,
    CaseBatchUpdateRequest,
    CaseBrief,
    CaseCreateRequest,
    CaseDetail,
    CaseListQuery,
    CaseReorderRequest,
    CaseUpdateRequest,
    PaginatedCases,
    TestPointBrief,
)
from service.functional_test.case.suite_guard import assert_case_deletable, assert_cases_deletable
from service.project.models import ProjectModule
from service.user.models import User


class CaseService:
    @classmethod
    async def _get_case_or_404(cls, case_id: int) -> FunctionalCase:
        case = await FunctionalCase.get_or_none(id=case_id)
        if case is None:
            raise AppException("用例不存在", 404)
        return case

    @classmethod
    async def _validate_module(cls, project_id: int, module_id: int | None) -> None:
        if module_id is None:
            return
        exists = await ProjectModule.filter(id=module_id, project_id=project_id).exists()
        if not exists:
            raise AppException("项目模块不存在", 404)

    @classmethod
    async def _validate_catalog(cls, project_id: int, catalog_id: int) -> FunctionalCaseCatalog:
        return await CatalogService._get_catalog_or_404(catalog_id, project_id)

    @classmethod
    async def _next_sort_order(cls, catalog_id: int) -> int:
        last = (
            await FunctionalCase.filter(catalog_id=catalog_id)
            .order_by("-sort_order")
            .first()
        )
        return (last.sort_order + 1) if last else 0

    @classmethod
    async def _to_brief(cls, case: FunctionalCase) -> CaseBrief:
        await case.fetch_related("catalog", "created_by")
        return CaseBrief(
            id=case.id,
            project_id=case.project_id,
            catalog_id=case.catalog_id,
            catalog_name=case.catalog.name if case.catalog else None,
            case_name=case.case_name,
            case_no=case.case_no,
            priority=case.priority,
            dimension=case.dimension,
            type=case.type,
            status=case.status,
            exec_result=case.exec_result,
            source=case.source,
            sort_order=case.sort_order,
            jira_issue_key=case.jira_issue_key,
            created_by_username=case.created_by.username if case.created_by else None,
            updated_at=case.updated_at,
        )

    @classmethod
    async def _to_detail(cls, case: FunctionalCase) -> CaseDetail:
        await case.fetch_related("test_point")
        brief = await cls._to_brief(case)
        tp = None
        if case.test_point:
            tp = TestPointBrief(
                id=case.test_point.id,
                type=case.test_point.type,
                dimension=case.test_point.dimension,
                test_point=case.test_point.test_point,
                source=case.test_point.source,
            )
        return CaseDetail(
            **brief.model_dump(),
            module_id=case.module_id,
            requirement_id=case.requirement_id,
            preconditions=case.preconditions,
            test_steps=case.test_steps,
            test_data=case.test_data,
            expected_result=case.expected_result,
            actual_result=case.actual_result,
            test_point=tp,
            created_at=case.created_at,
        )

    @classmethod
    async def list_cases(cls, user: User, query: CaseListQuery) -> PaginatedCases:
        await ensure_case_viewer(query.project_id, user)
        qs = FunctionalCase.filter(project_id=query.project_id)
        catalog_ids = await CatalogService.collect_catalog_ids_with_descendants(
            query.project_id, query.catalog_id
        )
        if catalog_ids is not None:
            qs = qs.filter(catalog_id__in=catalog_ids)
        if query.case_name:
            qs = qs.filter(case_name__icontains=query.case_name.strip())
        qs = qs.order_by("sort_order", "id")
        total, rows = await paginate(qs, query.page, query.page_size)
        items = [await cls._to_brief(row) for row in rows]
        return PaginatedCases(
            total=total, page=query.page, page_size=query.page_size, items=items
        )

    @classmethod
    async def get_detail(cls, user: User, case_id: int) -> CaseDetail:
        case = await cls._get_case_or_404(case_id)
        await ensure_case_viewer(case.project_id, user)
        return await cls._to_detail(case)

    @classmethod
    async def create(cls, user: User, data: CaseCreateRequest) -> CaseDetail:
        await ensure_case_editor(data.project_id, user)
        await cls._validate_catalog(data.project_id, data.catalog_id)
        await cls._validate_module(data.project_id, data.module_id)
        case_name = data.case_name.strip()
        if not case_name:
            raise AppException("用例名称不能为空", 400)
        sort_order = await cls._next_sort_order(data.catalog_id)
        case = await FunctionalCase.create(
            project_id=data.project_id,
            catalog_id=data.catalog_id,
            module_id=data.module_id,
            requirement_id=data.requirement_id,
            case_name=case_name,
            priority=data.priority,
            dimension=data.dimension,
            type=data.type,
            preconditions=data.preconditions,
            test_steps=data.test_steps,
            test_data=data.test_data,
            expected_result=data.expected_result,
            source=SourceType.manual,
            exec_result=FunctionalExecResult.pending,
            sort_order=sort_order,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        return await cls._to_detail(case)

    @classmethod
    async def update(cls, user: User, case_id: int, data: CaseUpdateRequest) -> CaseDetail:
        case = await cls._get_case_or_404(case_id)
        await ensure_case_editor(case.project_id, user)
        if data.catalog_id is not None:
            await cls._validate_catalog(case.project_id, data.catalog_id)
            case.catalog_id = data.catalog_id
        if data.module_id is not None:
            await cls._validate_module(case.project_id, data.module_id)
            case.module_id = data.module_id
        if data.requirement_id is not None:
            case.requirement_id = data.requirement_id
        if data.case_name is not None:
            name = data.case_name.strip()
            if not name:
                raise AppException("用例名称不能为空", 400)
            case.case_name = name
        for field in (
            "priority",
            "dimension",
            "type",
            "status",
            "exec_result",
            "preconditions",
            "test_steps",
            "test_data",
            "expected_result",
            "actual_result",
            "jira_issue_key",
        ):
            value = getattr(data, field)
            if value is not None:
                setattr(case, field, value)
        if data.test_point_summary is not None and case.test_point_id:
            tp = await FunctionalTestPoint.get_or_none(id=case.test_point_id)
            if tp is not None:
                tp.test_point = data.test_point_summary
                await tp.save(update_fields=["test_point"])
        case.updated_by_id = user.id
        await case.save()
        return await cls._to_detail(case)

    @classmethod
    async def delete(cls, user: User, case_id: int) -> None:
        case = await cls._get_case_or_404(case_id)
        await ensure_case_editor(case.project_id, user)
        suite_names = await assert_case_deletable(case_id)
        if suite_names:
            raise AppException(
                "用例已被测试套件引用，无法删除",
                409,
                data={"suite_names": suite_names},
            )
        await case.delete()

    @classmethod
    async def copy(cls, user: User, case_id: int) -> CaseDetail:
        case = await cls._get_case_or_404(case_id)
        await ensure_case_editor(case.project_id, user)
        new_name = cls._copy_name(case.case_name)
        sort_order = await cls._next_sort_order(case.catalog_id) if case.catalog_id else case.sort_order + 1
        copied = await FunctionalCase.create(
            project_id=case.project_id,
            catalog_id=case.catalog_id,
            module_id=case.module_id,
            requirement_id=case.requirement_id,
            test_point_id=case.test_point_id,
            case_no=case.case_no,
            case_name=new_name,
            priority=case.priority,
            dimension=case.dimension,
            type=case.type,
            status=case.status,
            exec_result=FunctionalExecResult.pending,
            content_format=case.content_format,
            preconditions=case.preconditions,
            test_steps=case.test_steps,
            test_data=case.test_data,
            expected_result=case.expected_result,
            source=case.source,
            sort_order=sort_order,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        return await cls._to_detail(copied)

    @staticmethod
    def _copy_name(name: str) -> str:
        base = re.sub(r"_copy(\d*)$", "", name)
        suffix = 1
        candidate = f"{base}_copy"
        while suffix < 1000:
            if candidate != name:
                return candidate
            suffix += 1
            candidate = f"{base}_copy{suffix}"
        return f"{base}_copy{suffix}"

    @classmethod
    async def reorder(cls, user: User, data: CaseReorderRequest) -> None:
        first = await FunctionalCase.get_or_none(id=data.ordered_ids[0])
        if first is None:
            raise AppException("用例不存在", 404)
        await ensure_case_editor(first.project_id, user)
        await cls._validate_catalog(first.project_id, data.catalog_id)
        cases = await FunctionalCase.filter(
            id__in=data.ordered_ids, catalog_id=data.catalog_id
        )
        case_map = {c.id: c for c in cases}
        if len(case_map) != len(set(data.ordered_ids)):
            raise AppException("排序用例与目录不匹配", 400)
        for idx, case_id in enumerate(data.ordered_ids):
            case_map[case_id].sort_order = idx
            case_map[case_id].updated_by_id = user.id
        for case in case_map.values():
            await case.save(update_fields=["sort_order", "updated_by_id"])

    @classmethod
    async def batch_update(cls, user: User, data: CaseBatchUpdateRequest) -> CaseBatchResult:
        if all(
            v is None
            for v in (data.priority, data.status, data.exec_result, data.catalog_id, data.module_id)
        ):
            raise AppException("批量更新字段不能全为空", 400)

        failures: list[BatchOperationFailure] = []
        success_count = 0
        for case_id in data.case_ids:
            case = await FunctionalCase.get_or_none(id=case_id)
            if case is None:
                failures.append(BatchOperationFailure(case_id=case_id, reason="用例不存在"))
                continue
            try:
                await ensure_case_editor(case.project_id, user)
                if data.catalog_id is not None:
                    await cls._validate_catalog(case.project_id, data.catalog_id)
                    case.catalog_id = data.catalog_id
                if data.module_id is not None:
                    await cls._validate_module(case.project_id, data.module_id)
                    case.module_id = data.module_id
                if data.priority is not None:
                    case.priority = data.priority
                if data.status is not None:
                    case.status = data.status
                if data.exec_result is not None:
                    case.exec_result = data.exec_result
                case.updated_by_id = user.id
                await case.save()
                success_count += 1
            except AppException as exc:
                failures.append(BatchOperationFailure(case_id=case_id, reason=exc.message))
        return CaseBatchResult(success_count=success_count, failures=failures)

    @classmethod
    async def batch_delete(cls, user: User, data: CaseBatchDeleteRequest) -> CaseBatchResult:
        blocked = await assert_cases_deletable(data.case_ids)
        failures: list[BatchOperationFailure] = []
        success_count = 0
        for case_id in data.case_ids:
            if case_id in blocked:
                failures.append(
                    BatchOperationFailure(
                        case_id=case_id,
                        reason=f"已被套件引用: {', '.join(blocked[case_id])}",
                    )
                )
                continue
            case = await FunctionalCase.get_or_none(id=case_id)
            if case is None:
                failures.append(BatchOperationFailure(case_id=case_id, reason="用例不存在"))
                continue
            try:
                await ensure_case_editor(case.project_id, user)
                await case.delete()
                success_count += 1
            except AppException as exc:
                failures.append(BatchOperationFailure(case_id=case_id, reason=exc.message))
        return CaseBatchResult(success_count=success_count, failures=failures)
