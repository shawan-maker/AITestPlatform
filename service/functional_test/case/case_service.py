"""功能测试模块 - case/case_service

业务逻辑服务
"""
import re

from service.core.enums import CaseCategory, SourceType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.functional_test.case.catalog_service import CatalogService
from service.functional_test.case.models import FunctionalCase, FunctionalCaseCatalog, FunctionalTestPoint
from service.functional_test.permissions import ensure_case_editor, ensure_case_viewer
from service.functional_test.case.schemas import (
    BatchOperationFailure,
    CaseBatchDeleteRequest,
    CaseBatchMoveRequest,
    CaseBatchCopyRequest,
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
from service.functional_test.case.suite_guard import (
    auto_remove_relations_for_cases,
    get_suite_names_for_cases,
)
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
    async def _ensure_name_unique_in_catalog(
        cls,
        case_name: str,
        catalog_id: int,
        *,
        exclude_id: int | None = None,
    ) -> None:
        qs = FunctionalCase.filter(catalog_id=catalog_id, case_name=case_name)
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if await qs.exists():
            raise AppException("同级目录下用例名称已存在", 409)

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
        await case.fetch_related("catalog", "created_by", "updated_by", "module")
        return CaseBrief(
            id=case.id,
            project_id=case.project_id,
            catalog_id=case.catalog_id,
            catalog_name=case.catalog.name if case.catalog else None,
            case_name=case.case_name,
            case_no=case.case_no,
            priority=case.priority,
            dimension=case.dimension,
            case_category=case.case_category,
            status=case.status,
            source=case.source,
            sort_order=case.sort_order,
            module_name=case.module.name if case.module else None,
            created_by_username=case.created_by.username if case.created_by else None,
            updated_by_username=case.updated_by.username if case.updated_by else None,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    @classmethod
    async def _to_detail(cls, case: FunctionalCase) -> CaseDetail:
        await case.fetch_related("test_point")
        brief = await cls._to_brief(case)
        
        test_point_value = case.test_point.test_point if case.test_point else None
        
        return CaseDetail(
            **brief.model_dump(),
            module_id=case.module_id,
            preconditions=case.preconditions,
            test_steps=case.test_steps,
            test_data=case.test_data,
            expected_result=case.expected_result,
            test_point=test_point_value,
        )

    @classmethod
    async def list_cases(cls, user: User, query: CaseListQuery) -> PaginatedCases:
        try:
            await ensure_case_viewer(query.project_id, user)
            qs = FunctionalCase.filter(project_id=query.project_id)
            catalog_ids = await CatalogService.collect_catalog_ids_with_descendants(
                query.project_id, query.catalog_id
            )
            if catalog_ids is not None:
                qs = qs.filter(catalog_id__in=catalog_ids)
            if query.case_name:
                qs = qs.filter(case_name__icontains=query.case_name.strip())
            if query.priority is not None:
                qs = qs.filter(priority=query.priority)
            if query.case_category is not None:
                qs = qs.filter(case_category=query.case_category)
            # 处理排序
            if query.sort_field and query.sort_order:
                # 映射前端字段名到模型字段名
                field_map = {
                    "priority": "priority",
                    "updated_at": "updated_at",
                }
                db_field = field_map.get(query.sort_field, "sort_order")
                order_prefix = "-" if query.sort_order == "desc" else ""
                qs = qs.order_by(f"{order_prefix}{db_field}", "id")
            else:
                qs = qs.order_by("sort_order", "id")
            total, rows = await paginate(qs, query.page, query.page_size)
            items = [await cls._to_brief(row) for row in rows]
            return PaginatedCases(
                total=total, page=query.page, page_size=query.page_size, items=items
            )
        except Exception as e:
            raise  # 重新抛出异常，让 FastAPI 处理

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
        await cls._ensure_name_unique_in_catalog(case_name, data.catalog_id)
        sort_order = await cls._next_sort_order(data.catalog_id)
        
        # 生成 case_no：项目标识 + 自增序号
        from service.project.models import Project
        project = await Project.get_or_none(id=data.project_id)
        if project:
            # 查询当前项目最大的 case_no 序号
            cases_with_no = await FunctionalCase.filter(
                project_id=data.project_id,
                case_no__not_isnull=True
            ).order_by("-case_no").first()
            
            if cases_with_no and cases_with_no.case_no:
                # 提取序号部分
                try:
                    seq = int(cases_with_no.case_no.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            
            # 项目标识取项目名称前4位大写
            prefix = (project.name or "PROJ")[:4].upper()
            case_no = f"{prefix}-{seq:04d}"
        else:
            case_no = None

        case = await FunctionalCase.create(
            project_id=data.project_id,
            catalog_id=data.catalog_id,
            module_id=data.module_id,
            case_no=case_no,
            case_name=case_name,
            priority=data.priority,
            dimension=data.dimension,
            case_category=data.case_category,
            preconditions=data.preconditions,
            test_steps=data.test_steps,
            test_data=data.test_data,
            expected_result=data.expected_result,
            source=SourceType.manual,
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
        if data.case_name is not None:
            name = data.case_name.strip()
            if not name:
                raise AppException("用例名称不能为空", 400)
            target_catalog_id = data.catalog_id if data.catalog_id is not None else case.catalog_id
            if target_catalog_id is not None:
                await cls._ensure_name_unique_in_catalog(name, target_catalog_id, exclude_id=case.id)
            case.case_name = name
        for field in (
            "priority",
            "dimension",
            "case_category",
            "status",
            "preconditions",
            "test_steps",
            "test_data",
            "expected_result",
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
    async def delete(cls, user: User, case_id: int) -> dict:
        case = await cls._get_case_or_404(case_id)
        await ensure_case_editor(case.project_id, user)
        suite_names = await get_suite_names_for_cases([case_id])
        await auto_remove_relations_for_cases([case_id])
        await case.delete()
        result: dict = {}
        if suite_names:
            result["warning"] = {"suite_names": suite_names}
        return result

    @classmethod
    async def copy(cls, user: User, case_id: int) -> CaseDetail:
        case = await cls._get_case_or_404(case_id)
        await ensure_case_editor(case.project_id, user)
        new_name = cls._copy_name(case.case_name)
        if case.catalog_id:
            await cls._ensure_name_unique_in_catalog(new_name, case.catalog_id)
        sort_order = await cls._next_sort_order(case.catalog_id) if case.catalog_id else case.sort_order + 1
        
        # 生成新的 case_no
        from service.project.models import Project
        project = await Project.get_or_none(id=case.project_id)
        if project:
            cases_with_no = await FunctionalCase.filter(
                project_id=case.project_id,
                case_no__not_isnull=True
            ).order_by("-case_no").first()
            
            if cases_with_no and cases_with_no.case_no:
                try:
                    seq = int(cases_with_no.case_no.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            
            prefix = (project.name or "PROJ")[:4].upper()
            case_no = f"{prefix}-{seq:04d}"
        else:
            case_no = null

        copied = await FunctionalCase.create(
            project_id=case.project_id,
            catalog_id=case.catalog_id,
            module_id=case.module_id,
            test_point_id=case.test_point_id,
            case_no=case_no,
            case_name=new_name,
            priority=case.priority,
            dimension=case.dimension,
            case_category=case.case_category,
            status=case.status,
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
        # 如果没有指定目录，则跳过排序
        if data.catalog_id is None:
            return
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
            for v in (
                data.case_category,
                data.priority,
                data.status,
                data.catalog_id,
                data.module_id,
                data.preconditions,
                data.test_steps,
                data.test_data,
                data.expected_result,
            )
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
                if data.case_category is not None:
                    case.case_category = data.case_category
                if data.priority is not None:
                    case.priority = data.priority
                if data.status is not None:
                    case.status = data.status
                if data.catalog_id is not None:
                    await cls._validate_catalog(case.project_id, data.catalog_id)
                    case.catalog_id = data.catalog_id
                if data.module_id is not None:
                    await cls._validate_module(case.project_id, data.module_id)
                    case.module_id = data.module_id
                if data.preconditions is not None:
                    case.preconditions = data.preconditions
                if data.test_steps is not None:
                    case.test_steps = data.test_steps
                if data.test_data is not None:
                    case.test_data = data.test_data
                if data.expected_result is not None:
                    case.expected_result = data.expected_result
                case.updated_by_id = user.id
                await case.save()
                success_count += 1
            except AppException as exc:
                failures.append(BatchOperationFailure(case_id=case_id, reason=exc.message))
        return CaseBatchResult(success_count=success_count, failures=failures)

    @classmethod
    async def batch_delete(cls, user: User, data: CaseBatchDeleteRequest) -> CaseBatchResult:
        failures: list[BatchOperationFailure] = []
        success_count = 0
        all_suite_names: list[str] = []
        for case_id in data.case_ids:
            case = await FunctionalCase.get_or_none(id=case_id)
            if case is None:
                failures.append(BatchOperationFailure(case_id=case_id, reason="用例不存在"))
                continue
            try:
                await ensure_case_editor(case.project_id, user)
                suite_names = await get_suite_names_for_cases([case_id])
                all_suite_names.extend(suite_names)
                await auto_remove_relations_for_cases([case_id])
                await case.delete()
                success_count += 1
            except AppException as exc:
                failures.append(BatchOperationFailure(case_id=case_id, reason=exc.message))
        result = CaseBatchResult(success_count=success_count, failures=failures)
        if all_suite_names:
            # 去重套件名称附加到结果中
            result.warning = {"suite_names": list(dict.fromkeys(all_suite_names))}
        return result

    @classmethod
    async def batch_move(cls, user: User, data: CaseBatchMoveRequest) -> CaseBatchResult:
        """批量移动用例到目标目录"""
        await CatalogService._get_catalog_or_404(data.target_catalog_id, user.project_id if hasattr(user, 'project_id') else None)
        
        failures: list[BatchOperationFailure] = []
        success_count = 0
        
        for case_id in data.case_ids:
            case = await FunctionalCase.get_or_none(id=case_id)
            if case is None:
                failures.append(BatchOperationFailure(case_id=case_id, reason="用例不存在"))
                continue
            try:
                await ensure_case_editor(case.project_id, user)
                # 检查目标目录是否有效
                target_catalog = await CatalogService._get_catalog_or_404(data.target_catalog_id, case.project_id)
                # 检查名称唯一性
                if case.catalog_id != data.target_catalog_id:
                    await cls._ensure_name_unique_in_catalog(case.case_name, data.target_catalog_id)
                # 更新目录
                case.catalog_id = data.target_catalog_id
                case.updated_by_id = user.id
                await case.save()
                success_count += 1
            except AppException as exc:
                failures.append(BatchOperationFailure(case_id=case_id, reason=exc.message))
            except Exception as e:
                failures.append(BatchOperationFailure(case_id=case_id, reason=str(e)))
        
        return CaseBatchResult(success_count=success_count, failures=failures)

    @classmethod
    async def batch_copy(cls, user: User, data: CaseBatchCopyRequest) -> CaseBatchResult:
        """批量复制用例到目标目录"""
        await CatalogService._get_catalog_or_404(data.target_catalog_id, user.project_id if hasattr(user, 'project_id') else None)
        
        failures: list[BatchOperationFailure] = []
        success_count = 0
        
        for case_id in data.case_ids:
            case = await FunctionalCase.get_or_none(id=case_id)
            if case is None:
                failures.append(BatchOperationFailure(case_id=case_id, reason="用例不存在"))
                continue
            try:
                await ensure_case_editor(case.project_id, user)
                # 生成新名称
                new_name = cls._copy_name(case.case_name)
                if data.target_catalog_id:
                    await cls._ensure_name_unique_in_catalog(new_name, data.target_catalog_id)
                
                # 获取项目信息生成 case_no
                from service.project.models import Project
                project = await Project.get_or_none(id=case.project_id)
                if project:
                    cases_with_no = await FunctionalCase.filter(
                        project_id=case.project_id,
                        case_no__not_isnull=True
                    ).order_by("-case_no").first()
                    
                    if cases_with_no and cases_with_no.case_no:
                        try:
                            seq = int(cases_with_no.case_no.split("-")[-1]) + 1
                        except (ValueError, IndexError):
                            seq = 1
                    else:
                        seq = 1
                    
                    prefix = (project.name or "PROJ")[:4].upper()
                    case_no = f"{prefix}-{seq:04d}"
                else:
                    case_no = None
                
                # 复制用例
                sort_order = await cls._next_sort_order(data.target_catalog_id)
                copied = await FunctionalCase.create(
                    project_id=case.project_id,
                    catalog_id=data.target_catalog_id,
                    module_id=case.module_id,
                    test_point_id=case.test_point_id,
                    case_no=case_no,
                    case_name=new_name,
                    priority=case.priority,
                    dimension=case.dimension,
                    case_category=case.case_category,
                    status=case.status,
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
                success_count += 1
            except AppException as exc:
                failures.append(BatchOperationFailure(case_id=case_id, reason=exc.message))
            except Exception as e:
                failures.append(BatchOperationFailure(case_id=case_id, reason=str(e)))
        
        return CaseBatchResult(success_count=success_count, failures=failures)
