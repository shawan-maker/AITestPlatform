from service.core.exceptions import AppException
from service.functional_test.case.models import FunctionalCase, FunctionalCaseCatalog
from service.functional_test.permissions import ensure_case_editor, ensure_case_viewer
from service.functional_test.case.schemas import (
    CatalogCreateRequest,
    CatalogMoveRequest,
    CatalogOut,
    CatalogTreeNode,
    CatalogUpdateRequest,
)
from service.user.models import User


class CatalogService:
    MAX_LEVEL = 5

    @classmethod
    async def _get_catalog_or_404(
        cls, catalog_id: int, project_id: int | None = None
    ) -> FunctionalCaseCatalog:
        catalog = await FunctionalCaseCatalog.get_or_none(id=catalog_id)
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
        qs = FunctionalCaseCatalog.filter(
            project_id=project_id, parent_id=parent_id, name=name
        )
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if await qs.exists():
            raise AppException("同级目录名称已存在", 409)

    @classmethod
    async def _collect_subtree_ids(cls, root_id: int) -> set[int]:
        catalogs = await FunctionalCaseCatalog.all().values("id", "parent_id")
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
    async def _subtree_has_cases(cls, catalog_id: int) -> bool:
        ids = await cls._collect_subtree_ids(catalog_id)
        return await FunctionalCase.filter(catalog_id__in=list(ids)).exists()

    @classmethod
    async def get_tree(cls, user: User, project_id: int) -> list[CatalogTreeNode]:
        await ensure_case_viewer(project_id, user)
        catalogs = await FunctionalCaseCatalog.filter(project_id=project_id).order_by(
            "level", "sort_order", "id"
        )
        case_counts: dict[int | None, int] = {}
        cases = await FunctionalCase.filter(project_id=project_id).values("catalog_id")
        for row in cases:
            key = row["catalog_id"]
            case_counts[key] = case_counts.get(key, 0) + 1

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
                case_count=case_counts.get(cat.id, 0),
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
        await ensure_case_editor(project_id, user)
        level = 1
        if data.parent_id is not None:
            parent = await cls._get_catalog_or_404(data.parent_id, project_id)
            if parent.level >= cls.MAX_LEVEL:
                raise AppException(f"目录层级不能超过 {cls.MAX_LEVEL} 级", 400)
            level = parent.level + 1
        name = data.name.strip()
        await cls._ensure_unique_sibling_name(project_id, data.parent_id, name)
        catalog = await FunctionalCaseCatalog.create(
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
        await ensure_case_editor(catalog.project_id, user)
        parent_id = catalog.parent_id if data.parent_id is None else data.parent_id
        name = catalog.name if data.name is None else data.name.strip()
        level = catalog.level

        if data.parent_id is not None:
            if data.parent_id == catalog_id:
                raise AppException("不能将目录移动到自身", 400)
            if data.parent_id == 0:
                parent_id = None
                level = 1
            else:
                parent = await cls._get_catalog_or_404(data.parent_id, catalog.project_id)
                if parent.level >= cls.MAX_LEVEL:
                    raise AppException(f"目录层级不能超过 {cls.MAX_LEVEL} 级", 400)
                level = parent.level + 1
                parent_id = data.parent_id

        if data.name is not None or data.parent_id is not None:
            await cls._ensure_unique_sibling_name(
                catalog.project_id, parent_id, name, exclude_id=catalog.id
            )
        if data.name is not None:
            catalog.name = name
        if data.parent_id is not None:
            catalog.parent_id = parent_id
            catalog.level = level
        await catalog.save()
        return cls._to_out(catalog)

    @classmethod
    async def move(
        cls, user: User, catalog_id: int, data: CatalogMoveRequest
    ) -> CatalogOut:
        catalog = await cls._get_catalog_or_404(catalog_id)
        await ensure_case_editor(catalog.project_id, user)
        if data.parent_id is not None:
            if data.parent_id == catalog_id:
                raise AppException("不能将目录移动到自身", 400)
            if data.parent_id == 0:
                catalog.parent_id = None
                catalog.level = 1
            else:
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
        await ensure_case_editor(catalog.project_id, user)
        if await cls._subtree_has_cases(catalog_id):
            raise AppException("目录或其子目录下存在用例，无法删除", 400)
        await cls._delete_empty_subtree(catalog_id)

    @classmethod
    async def _delete_empty_subtree(cls, catalog_id: int) -> None:
        children = await FunctionalCaseCatalog.filter(parent_id=catalog_id)
        for child in children:
            if not await cls._subtree_has_cases(child.id):
                await cls._delete_empty_subtree(child.id)
        await FunctionalCaseCatalog.filter(id=catalog_id).delete()

    @staticmethod
    def _to_out(catalog: FunctionalCaseCatalog) -> CatalogOut:
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
