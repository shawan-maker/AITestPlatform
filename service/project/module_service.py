"""项目管理模块 - module_service

业务逻辑服务
"""
from service.api_test.models import ApiInterface
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.functional_test.case.models import FunctionalCase
from service.knowledge.models import KnowledgeDocument
from service.project.models import ProjectModule
from service.project.permissions import ensure_project_editor, ensure_project_viewer
from service.project.schemas import (
    PaginatedProjectModules,
    ProjectModuleBrief,
    ProjectModuleCreateRequest,
    ProjectModuleUpdateRequest,
)
from service.user.models import User


class ModuleService:
    @classmethod
    async def _get_module_or_404(cls, project_id: int, module_id: int) -> ProjectModule:
        module = await ProjectModule.get_or_none(id=module_id, project_id=project_id)
        if module is None:
            raise AppException("项目模块不存在", 404)
        return module

    @classmethod
    async def _ensure_unique_name(
        cls,
        project_id: int,
        name: str,
        exclude_id: int | None = None,
    ) -> None:
        qs = ProjectModule.filter(project_id=project_id, name=name)
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if await qs.exists():
            raise AppException("同级模块名称已存在", 409)

    @classmethod
    async def _ensure_deletable(cls, module_id: int) -> None:
        blockers: list[str] = []
        if await FunctionalCase.filter(module_id=module_id).exists():
            blockers.append("功能用例")
        if await ApiInterface.filter(module_id=module_id, is_current=True).exists():
            blockers.append("接口定义")
        if await KnowledgeDocument.filter(module_id=module_id).exists():
            blockers.append("知识库文档")
        if blockers:
            raise AppException(
                f"模块已被{'、'.join(blockers)}引用，无法删除",
                409,
            )

    @classmethod
    async def list_modules(
        cls,
        user: User,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedProjectModules:
        await ensure_project_viewer(project_id, user)
        qs = ProjectModule.filter(project_id=project_id).order_by("id")
        total, items = await paginate(qs, page, page_size)
        return PaginatedProjectModules(
            total=total,
            page=page,
            page_size=page_size,
            items=[cls._to_brief(m) for m in items],
        )

    @classmethod
    async def create_module(
        cls,
        user: User,
        project_id: int,
        data: ProjectModuleCreateRequest,
    ) -> ProjectModuleBrief:
        await ensure_project_editor(project_id, user)
        await cls._ensure_unique_name(project_id, data.name)
        module = await ProjectModule.create(
            project_id=project_id,
            name=data.name,
            description=data.description,
        )
        return cls._to_brief(module)

    @classmethod
    async def update_module(
        cls,
        user: User,
        project_id: int,
        module_id: int,
        data: ProjectModuleUpdateRequest,
    ) -> ProjectModuleBrief:
        await ensure_project_editor(project_id, user)
        module = await cls._get_module_or_404(project_id, module_id)
        name = module.name if data.name is None else data.name
        if data.name is not None:
            await cls._ensure_unique_name(project_id, name, exclude_id=module.id)
            module.name = name
        if data.description is not None:
            module.description = data.description
        await module.save()
        return cls._to_brief(module)

    @classmethod
    async def delete_module(cls, user: User, project_id: int, module_id: int) -> None:
        await ensure_project_editor(project_id, user)
        module = await cls._get_module_or_404(project_id, module_id)
        await cls._ensure_deletable(module_id)
        await module.delete()

    @staticmethod
    def _to_brief(module: ProjectModule) -> ProjectModuleBrief:
        return ProjectModuleBrief(
            id=module.id,
            project_id=module.project_id,
            name=module.name,
            description=module.description,
            created_at=module.created_at,
            updated_at=module.updated_at,
        )
