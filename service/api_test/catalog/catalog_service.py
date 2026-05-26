from service.api_test.catalog.schemas import (
    CatalogCreateRequest,
    CatalogMoveRequest,
    CatalogOut,
    CatalogTreeNode,
    CatalogUpdateRequest,
)
from service.api_test.interface.models import ApiInterface, ApiInterfaceCatalog
from service.api_test.permissions import ensure_api_editor, ensure_api_viewer
from service.core.exceptions import AppException
from service.user.models import User


class CatalogService:
    MAX_LEVEL = 5

    @classmethod
    async def _get_catalog_or_404(
        cls, catalog_id: int, project_id: int | None = None
    ) -> ApiInterfaceCatalog:
        catalog = await ApiInterfaceCatalog.get_or_none(id=catalog_id)
        if catalog is None:
            raise AppException("目录不存在", 404)
        if project_id is not None and catalog.project_id != project_id:
            raise AppException("目录不存在", 404)
        return catalog

    @classmethod
    async def _ensure_unique_sibling_name(
        cls,
        project_id: int,
        parent_id: int | None,
        name: str,
        exclude_id: int | None = None,
    ) -> None:
        qs = ApiInterfaceCatalog.filter(
            project_id=project_id, parent_id=parent_id, name=name
        )
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if await qs.exists():
            raise AppException("同级目录名称已存在", 409)

    @classmethod
    async def _collect_subtree_ids(cls, root_id: int) -> set[int]:
        catalogs = await ApiInterfaceCatalog.all().values("id", "parent_id")
        children_map: dict[int | None, list[int]] = {}
        for row in catalogs:
            children_map.setdefault(row["parent_id"], []).append(row["id"])
        result: set[int] = set()
        stack = [root_id]
        while stack:
            cid = stack.pop()
            if cid in result:
                continue
            result.add(cid)
            stack.extend(children_map.get(cid, []))
        return result

    @classmethod
    async def _interface_counts_in_subtrees(
        cls, project_id: int
    ) -> dict[int, int]:
        catalogs = await ApiInterfaceCatalog.filter(project_id=project_id).values(
            "id", "parent_id"
        )
        children_map: dict[int | None, list[int]] = {}
        for row in catalogs:
            children_map.setdefault(row["parent_id"], []).append(row["id"])

        direct: dict[int, int] = {}
        interfaces = await ApiInterface.filter(
            project_id=project_id, is_current=True
        ).values("catalog_id")
        for row in interfaces:
            cid = row["catalog_id"]
            if cid is not None:
                direct[cid] = direct.get(cid, 0) + 1

        totals: dict[int, int] = {}

        def subtree_total(node_id: int) -> int:
            if node_id in totals:
                return totals[node_id]
            total = direct.get(node_id, 0)
            for child_id in children_map.get(node_id, []):
                total += subtree_total(child_id)
            totals[node_id] = total
            return total

        for row in catalogs:
            subtree_total(row["id"])
        return totals

    @classmethod
    async def get_tree(cls, user: User, project_id: int) -> list[CatalogTreeNode]:
        await ensure_api_viewer(project_id, user)
        catalogs = await ApiInterfaceCatalog.filter(project_id=project_id).order_by(
            "level", "sort_order", "id"
        )
        counts = await cls._interface_counts_in_subtrees(project_id)
        nodes: dict[int, CatalogTreeNode] = {}
        roots: list[CatalogTreeNode] = []
        for cat in catalogs:
            node = CatalogTreeNode(
                id=cat.id,
                project_id=cat.project_id,
                parent_id=cat.parent_id,
                name=cat.name,
                level=cat.level,
                sort_order=cat.sort_order,
                interface_count=counts.get(cat.id, 0),
                children=[],
                created_at=cat.created_at,
                updated_at=cat.updated_at,
            )
            nodes[cat.id] = node
        for cat in catalogs:
            node = nodes[cat.id]
            if cat.parent_id and cat.parent_id in nodes:
                nodes[cat.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots

    @classmethod
    async def create(
        cls, user: User, project_id: int, data: CatalogCreateRequest
    ) -> CatalogOut:
        await ensure_api_editor(project_id, user)
        level = 1
        if data.parent_id is not None:
            parent = await cls._get_catalog_or_404(data.parent_id, project_id)
            if parent.level >= cls.MAX_LEVEL:
                raise AppException(f"目录层级不能超过 {cls.MAX_LEVEL} 级", 400)
            level = parent.level + 1
        name = data.name.strip()
        await cls._ensure_unique_sibling_name(project_id, data.parent_id, name)
        catalog = await ApiInterfaceCatalog.create(
            project_id=project_id,
            parent_id=data.parent_id,
            name=name,
            level=level,
        )
        return cls._to_out(catalog)

    @classmethod
    async def update(
        cls, user: User, catalog_id: int, data: CatalogUpdateRequest
    ) -> CatalogOut:
        catalog = await cls._get_catalog_or_404(catalog_id)
        await ensure_api_editor(catalog.project_id, user)
        if data.name is not None:
            name = data.name.strip()
            await cls._ensure_unique_sibling_name(
                catalog.project_id, catalog.parent_id, name, exclude_id=catalog.id
            )
            catalog.name = name
            await catalog.save()
        return cls._to_out(catalog)

    @classmethod
    async def move(
        cls, user: User, catalog_id: int, data: CatalogMoveRequest
    ) -> CatalogOut:
        catalog = await cls._get_catalog_or_404(catalog_id)
        await ensure_api_editor(catalog.project_id, user)
        if data.parent_id is not None:
            if data.parent_id == catalog_id:
                raise AppException("不能将目录移动到自身", 400)
            parent = await cls._get_catalog_or_404(data.parent_id, catalog.project_id)
            if parent.level >= cls.MAX_LEVEL:
                raise AppException(f"目录层级不能超过 {cls.MAX_LEVEL} 级", 409)
            subtree_ids = await cls._collect_subtree_ids(catalog_id)
            if data.parent_id in subtree_ids:
                raise AppException("不能将目录移动到其子目录下", 400)
            catalog.parent_id = data.parent_id
            catalog.level = parent.level + 1
        if data.sort_order is not None:
            catalog.sort_order = data.sort_order
        await catalog.save()
        return cls._to_out(catalog)

    @classmethod
    async def delete(cls, user: User, catalog_id: int) -> None:
        catalog = await cls._get_catalog_or_404(catalog_id)
        await ensure_api_editor(catalog.project_id, user)
        subtree_ids = list(await cls._collect_subtree_ids(catalog_id))
        from service.api_test.interface.interface_service import InterfaceService

        await InterfaceService.delete_by_catalog_ids(catalog.project_id, subtree_ids)
        await ApiInterfaceCatalog.filter(id__in=subtree_ids).delete()

    @staticmethod
    def _to_out(catalog: ApiInterfaceCatalog) -> CatalogOut:
        return CatalogOut(
            id=catalog.id,
            project_id=catalog.project_id,
            parent_id=catalog.parent_id,
            name=catalog.name,
            level=catalog.level,
            sort_order=catalog.sort_order,
            created_at=catalog.created_at,
            updated_at=catalog.updated_at,
        )

    @classmethod
    async def collect_catalog_ids_with_descendants(
        cls, project_id: int, catalog_id: int | None
    ) -> list[int] | None:
        if catalog_id is None:
            return None
        catalog = await cls._get_catalog_or_404(catalog_id, project_id)
        return list(await cls._collect_subtree_ids(catalog.id))
