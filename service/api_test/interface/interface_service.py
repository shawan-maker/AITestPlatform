import re

from tortoise.expressions import Q

from service.api_test.interface.models import ApiInterface, ApiInterfaceCatalog
from service.api_test.interface.schemas import (
    InterfaceCreateRequest,
    InterfaceListQuery,
    InterfaceOut,
    InterfaceReorderRequest,
    InterfaceUpdateRequest,
    PaginatedInterfaces,
)
from service.api_test.interface.version_service import VersionService
from service.api_test.models import ApiBaseCase, ApiDependency, ApiDependencyGroup, ApiTestCase
from service.api_test.permissions import ensure_api_editor, ensure_api_viewer
from service.api_test.shared.suite_guard import remove_suite_relations_for_cases
from service.core.enums import ApiInterfaceSource
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.project.models import ProjectModule
from service.user.models import User


class InterfaceService:
    @classmethod
    async def _get_current_or_404(
        cls, interface_id: int, project_id: int | None = None
    ) -> ApiInterface:
        iface = await ApiInterface.get_or_none(id=interface_id, is_current=True)
        if iface is None:
            raise AppException("接口不存在", 404)
        if project_id is not None and iface.project_id != project_id:
            raise AppException("接口不存在", 404)
        return iface

    @classmethod
    def _to_out(cls, iface: ApiInterface, catalog_full_path: str | None = None) -> InterfaceOut:
        return InterfaceOut(
            id=iface.id,
            project_id=iface.project_id,
            catalog_id=iface.catalog_id,
            module_id=iface.module_id,
            method=iface.method,
            path=iface.path,
            summary=iface.summary,
            parameters=iface.parameters or {"header": [], "path": [], "query": []},
            request_body=iface.request_body,
            responses=iface.responses or [],
            source=iface.source,
            source_document_id=iface.source_document_id,
            source_document_version_id=iface.source_document_version_id,
            version=iface.version,
            is_current=iface.is_current,
            sort_order=iface.sort_order,
            created_at=iface.created_at,
            updated_at=iface.updated_at,
            catalog_full_path=catalog_full_path,
        )

    @classmethod
    async def _validate_catalog(cls, project_id: int, catalog_id: int) -> ApiInterfaceCatalog:
        catalog = await ApiInterfaceCatalog.get_or_none(id=catalog_id, project_id=project_id)
        if catalog is None:
            raise AppException("目录不存在", 404)
        return catalog

    @classmethod
    async def _validate_module(cls, project_id: int, module_id: int | None) -> None:
        if module_id is None:
            return
        if not await ProjectModule.filter(id=module_id, project_id=project_id).exists():
            raise AppException("项目模块不存在", 404)

    @classmethod
    async def _collect_catalog_ids_with_descendants(
        cls, project_id: int, catalog_id: int | None
    ) -> list[int] | None:
        if catalog_id is None:
            return None
        catalog = await ApiInterfaceCatalog.get_or_none(
            id=catalog_id, project_id=project_id
        )
        if catalog is None:
            raise AppException("目录不存在", 404)
        catalogs = await ApiInterfaceCatalog.filter(project_id=project_id).values(
            "id", "parent_id"
        )
        children_map: dict[int | None, list[int]] = {}
        for row in catalogs:
            children_map.setdefault(row["parent_id"], []).append(row["id"])
        result: set[int] = set()
        stack = [catalog.id]
        while stack:
            cid = stack.pop()
            if cid in result:
                continue
            result.add(cid)
            stack.extend(children_map.get(cid, []))
        return list(result)

    @classmethod
    async def _build_catalog_full_path(cls, catalog_id: int | None, project_id: int) -> str | None:
        """v2: 递归构建目录完整路径，格式: 一级/二级/三级"""
        if catalog_id is None:
            return None
        catalogs = await ApiInterfaceCatalog.filter(
            project_id=project_id
        ).values("id", "parent_id", "name")
        id_to_cat = {c["id"]: c for c in catalogs}
        if catalog_id not in id_to_cat:
            return None
        parts: list[str] = []
        cid = catalog_id
        visited = set()
        while cid is not None and cid not in visited:
            visited.add(cid)
            cat = id_to_cat.get(cid)
            if not cat:
                break
            parts.append(cat["name"])
            cid = cat.get("parent_id")
        parts.reverse()
        return " / ".join(parts)

    @classmethod
    async def list_interfaces(
        cls, user: User, query: InterfaceListQuery
    ) -> PaginatedInterfaces:
        await ensure_api_viewer(query.project_id, user)
        qs = ApiInterface.filter(project_id=query.project_id, is_current=True)
        # v2-L1: 默认全局搜索，可选按catalog_id筛选（含子目录）
        if query.catalog_id is not None:
            catalog_ids = await cls._collect_catalog_ids_with_descendants(
                query.project_id, query.catalog_id
            )
            qs = qs.filter(catalog_id__in=catalog_ids or [])
        if query.q:
            kw = query.q.strip()
            qs = qs.filter(Q(path__icontains=kw) | Q(summary__icontains=kw))
        qs = qs.order_by("sort_order", "id")
        total, items = await paginate(qs, query.page, query.page_size)
        # v2-Q5: 批量构建catalog_full_path
        out_items = []
        for iface in items:
            full_path = await cls._build_catalog_full_path(iface.catalog_id, query.project_id)
            out_items.append(cls._to_out(iface, catalog_full_path=full_path))
        return PaginatedInterfaces(
            total=total,
            page=query.page,
            page_size=query.page_size,
            items=out_items,
        )

    @classmethod
    async def list_by_catalog(
        cls,
        user: User,
        catalog_id: int,
        *,
        page: int,
        page_size: int,
    ) -> PaginatedInterfaces:
        catalog = await ApiInterfaceCatalog.get_or_none(id=catalog_id)
        if catalog is None:
            raise AppException("目录不存在", 404)
        await ensure_api_viewer(catalog.project_id, user)
        qs = ApiInterface.filter(
            catalog_id=catalog_id, is_current=True
        ).order_by("sort_order", "id")
        total, items = await paginate(qs, page, page_size)
        return PaginatedInterfaces(
            total=total,
            page=page,
            page_size=page_size,
            items=[cls._to_out(i) for i in items],
        )

    @classmethod
    async def get_detail(cls, user: User, interface_id: int) -> InterfaceOut:
        iface = await cls._get_current_or_404(interface_id)
        await ensure_api_viewer(iface.project_id, user)
        return cls._to_out(iface)

    @classmethod
    async def create(cls, user: User, data: InterfaceCreateRequest) -> InterfaceOut:
        await ensure_api_editor(data.project_id, user)
        await cls._validate_catalog(data.project_id, data.catalog_id)
        await cls._validate_module(data.project_id, data.module_id)
        method = data.method.upper()
        await VersionService.ensure_unique_current_path(data.project_id, method, data.path)
        iface = await ApiInterface.create(
            project_id=data.project_id,
            catalog_id=data.catalog_id,
            module_id=data.module_id,
            method=method,
            path=data.path,
            summary=data.summary,
            parameters=data.parameters
            or {"header": [], "path": [], "query": []},
            request_body=data.request_body,
            responses=data.responses or [],
            source=ApiInterfaceSource.manual,
            is_current=True,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        from service.api_test.dependency.merge_service import DependencyMergeService

        await DependencyMergeService.infer_and_persist(
            data.project_id, [iface.id], user_id=user.id
        )
        return cls._to_out(iface)

    @classmethod
    async def update(
        cls, user: User, interface_id: int, data: InterfaceUpdateRequest
    ) -> InterfaceOut:
        """v2修订: 白名单仅3字段(name/method/path)，其他字段忽略。改method/path走版本管理"""
        iface = await cls._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        # v2-Q1: 仅允许 name(summary)、method、path 三字段
        updates: dict = {}
        if data.name is not None:
            updates["summary"] = data.name

        method = data.method.upper() if data.method else iface.method
        path = data.path if data.path is not None else iface.path

        if data.method is not None or data.path is not None:
            # method或path变更 → 走版本管理(新行)
            iface = await VersionService.bump_version_on_identity_change(
                iface, method=method, path=path, user_id=user.id, updates=updates
            )
        elif updates:
            # 仅修改summary(name) → 原地更新
            setattr(iface, "summary", updates["summary"])
            iface.updated_by_id = user.id
            await iface.save()
        return cls._to_out(iface)

    @classmethod
    async def delete(cls, user: User, interface_id: int) -> None:
        iface = await cls._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        await cls._hard_delete_interfaces([iface.id])

    @classmethod
    async def batch_delete(cls, user: User, data) -> dict:
        deleted_ids = []
        failures = []
        for item_id in data.interface_ids:
            try:
                await cls.delete(user, item_id)
                deleted_ids.append(item_id)
            except AppException as e:
                failures.append({'interface_id': item_id, 'message': e.message})
            except Exception as e:
                failures.append({'interface_id': item_id, 'message': str(e)})
        return {'deleted_ids': deleted_ids, 'failures': failures}

    @classmethod
    async def delete_by_catalog_ids(
        cls, project_id: int, catalog_ids: list[int]
    ) -> None:
        iface_ids = await ApiInterface.filter(
            project_id=project_id, catalog_id__in=catalog_ids
        ).values_list("id", flat=True)
        await cls._hard_delete_interfaces(list(iface_ids))

    @classmethod
    async def _hard_delete_interfaces(cls, interface_ids: list[int]) -> None:
        if not interface_ids:
            return
        case_ids = await ApiTestCase.filter(
            interface_id__in=interface_ids
        ).values_list("id", flat=True)
        await remove_suite_relations_for_cases(list(case_ids))
        await ApiTestCase.filter(interface_id__in=interface_ids).delete()
        await ApiBaseCase.filter(interface_id__in=interface_ids).delete()
        group_ids = await ApiDependencyGroup.filter(
            target_api_id__in=interface_ids
        ).values_list("id", flat=True)
        if group_ids:
            await ApiDependency.filter(dependency_group_id__in=list(group_ids)).delete()
            await ApiDependencyGroup.filter(id__in=list(group_ids)).delete()
        await ApiDependency.filter(
            Q(from_api_id__in=interface_ids) | Q(to_api_id__in=interface_ids)
        ).delete()
        await ApiInterface.filter(id__in=interface_ids).delete()

    @classmethod
    async def _next_copy_path(cls, project_id: int, path: str) -> str:
        base = path.rstrip("/")
        pattern = re.compile(rf"^{re.escape(base)}/_copy(\d{{2}})$")
        existing = await ApiInterface.filter(
            project_id=project_id, is_current=True, path__startswith=f"{base}/_copy"
        ).values_list("path", flat=True)
        used = set()
        for p in existing:
            m = pattern.match(p)
            if m:
                used.add(int(m.group(1)))
        n = 1
        while n in used:
            n += 1
        return f"{base}/_copy{n:02d}"

    @classmethod
    async def copy(cls, user: User, interface_id: int) -> InterfaceOut:
        iface = await cls._get_current_or_404(interface_id)
        await ensure_api_editor(iface.project_id, user)
        new_path = await cls._next_copy_path(iface.project_id, iface.path)
        summary = iface.summary or ""
        if summary:
            summary = f"{summary}_copy01"[:255]
        new_iface = await ApiInterface.create(
            project_id=iface.project_id,
            catalog_id=iface.catalog_id,
            module_id=iface.module_id,
            method=iface.method,
            path=new_path,
            summary=summary or None,
            parameters=iface.parameters,
            request_body=iface.request_body,
            responses=iface.responses,
            source=iface.source,
            source_document_id=iface.source_document_id,
            source_document_version_id=iface.source_document_version_id,
            version=1,
            is_current=True,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        from service.api_test.dependency.merge_service import DependencyMergeService

        await DependencyMergeService.infer_and_persist(
            iface.project_id, [new_iface.id], user_id=user.id
        )
        return cls._to_out(new_iface)

    @classmethod
    async def reorder(cls, user: User, data: InterfaceReorderRequest) -> None:
        catalog = await ApiInterfaceCatalog.get_or_none(id=data.catalog_id)
        if catalog is None:
            raise AppException("目录不存在", 404)
        await ensure_api_editor(catalog.project_id, user)
        target_catalog_id = data.target_catalog_id or data.catalog_id
        if target_catalog_id != data.catalog_id:
            await cls._validate_catalog(catalog.project_id, target_catalog_id)
        for idx, iface_id in enumerate(data.ordered_ids):
            iface = await cls._get_current_or_404(iface_id, catalog.project_id)
            iface.catalog_id = target_catalog_id
            iface.sort_order = idx
            await iface.save(update_fields=["catalog_id", "sort_order", "updated_at"])
