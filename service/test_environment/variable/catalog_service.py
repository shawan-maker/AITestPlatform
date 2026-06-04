from service.core.exceptions import AppException
from service.test_environment.models import EnvCatalog, TestEnvironment
from service.test_environment.permissions import ensure_project_editor, ensure_project_viewer
from service.test_environment.variable.schemas import (
    CatalogCreateRequest,
    CatalogOut,
    CatalogTreeNode,
    CatalogUpdateRequest,
)
from service.user.models import User


class CatalogService:
    MAX_LEVEL = 5

    @classmethod
    async def _get_catalog_or_404(cls, catalog_id: int, project_id: int | None = None) -> EnvCatalog:
        catalog = await EnvCatalog.get_or_none(id=catalog_id)
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
        qs = EnvCatalog.filter(project_id=project_id, parent_id=parent_id, name=name)
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if await qs.exists():
            raise AppException("同级目录名称已存在", 409)

    @classmethod
    async def get_tree(cls, user: User, project_id: int) -> list[CatalogTreeNode]:
        await ensure_project_viewer(project_id, user)
        catalogs = await EnvCatalog.filter(project_id=project_id).order_by("level", "id")
        env_counts: dict[int | None, int] = {}
        environments = await TestEnvironment.filter(project_id=project_id)
        for env in environments:
            key = env.catalog_id
            env_counts[key] = env_counts.get(key, 0) + 1

        nodes: dict[int, CatalogTreeNode] = {}
        roots: list[CatalogTreeNode] = []
        for cat in catalogs:
            node = CatalogTreeNode(
                id=cat.id,
                name=cat.name,
                level=cat.level,
                parent_id=cat.parent_id,
                environment_count=env_counts.get(cat.id, 0),
                children=[],
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
    async def create(cls, user: User, project_id: int, data: CatalogCreateRequest) -> CatalogOut:
        await ensure_project_editor(project_id, user)
        level = 1
        if data.parent_id is not None:
            parent = await cls._get_catalog_or_404(data.parent_id, project_id)
            if parent.level >= cls.MAX_LEVEL:
                raise AppException("目录层级不能超过 3 级", 400)
            level = parent.level + 1
        await cls._ensure_unique_sibling_name(project_id, data.parent_id, data.name)
        catalog = await EnvCatalog.create(
            project_id=project_id,
            parent_id=data.parent_id,
            name=data.name,
            level=level,
        )
        return cls._to_out(catalog)

    @classmethod
    async def update(cls, user: User, catalog_id: int, data: CatalogUpdateRequest) -> CatalogOut:
        catalog = await cls._get_catalog_or_404(catalog_id)
        await ensure_project_editor(catalog.project_id, user)
        parent_id = catalog.parent_id if data.parent_id is None else data.parent_id
        name = catalog.name if data.name is None else data.name.strip()
        if data.parent_id is not None and data.parent_id == catalog_id:
            raise AppException("不能将目录移动到自身", 400)
        level = catalog.level
        if data.parent_id is not None:
            if data.parent_id == 0:
                parent_id = None
                level = 1
            else:
                parent = await cls._get_catalog_or_404(data.parent_id, catalog.project_id)
                if parent.level >= cls.MAX_LEVEL:
                    raise AppException("目录层级不能超过 3 级", 400)
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
    async def delete(cls, user: User, catalog_id: int) -> None:
        catalog = await cls._get_catalog_or_404(catalog_id)
        await ensure_project_editor(catalog.project_id, user)
        if await EnvCatalog.filter(parent_id=catalog_id).exists():
            raise AppException("目录下存在子目录，无法删除", 400)
        if await TestEnvironment.filter(catalog_id=catalog_id).exists():
            raise AppException("目录下存在变量文件，无法删除", 400)
        await catalog.delete()

    @staticmethod
    def _to_out(catalog: EnvCatalog) -> CatalogOut:
        return CatalogOut(
            id=catalog.id,
            project_id=catalog.project_id,
            parent_id=catalog.parent_id,
            name=catalog.name,
            level=catalog.level,
            created_at=catalog.created_at,
            updated_at=catalog.updated_at,
        )
