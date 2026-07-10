"""测试环境管理模块 - variable/environment_service

业务逻辑服务
"""
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.test_environment.models import (
    EnvCatalog,
    EnvironmentDbRelation,
    EnvironmentFunctionRelation,
    TestEnvironment,
)
from service.test_environment.permissions import ensure_project_editor, ensure_project_viewer
from service.test_environment.function.schemas import FunctionBindItem
from service.test_environment.variable.schemas import (
    EnvironmentBrief,
    EnvironmentCreateRequest,
    EnvironmentDetail,
    EnvironmentUpdateRequest,
    PaginatedEnvironments,
)
from service.user.models import User


class EnvironmentService:
    @classmethod
    async def _get_or_404(cls, environment_id: int) -> TestEnvironment:
        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise AppException("变量文件不存在", 404)
        return env

    @classmethod
    async def list_environments(
        cls,
        user: User,
        project_id: int,
        *,
        catalog_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedEnvironments:
        await ensure_project_viewer(project_id, user)
        qs = TestEnvironment.filter(project_id=project_id)
        if catalog_id is not None:
            qs = qs.filter(catalog_id=catalog_id)
        if keyword:
            qs = qs.filter(env_name__icontains=keyword.strip())
        qs = qs.order_by("-updated_at")
        total, items = await paginate(qs, page, page_size)
        return PaginatedEnvironments(
            total=total,
            page=page,
            page_size=page_size,
            items=[cls._to_brief(env) for env in items],
        )

    @classmethod
    async def create(
        cls, user: User, project_id: int, data: EnvironmentCreateRequest
    ) -> EnvironmentDetail:
        await ensure_project_editor(project_id, user)
        if await TestEnvironment.filter(project_id=project_id, env_name=data.env_name).exists():
            raise AppException("变量文件名称已存在", 409)
        if data.catalog_id is not None:
            catalog = await EnvCatalog.get_or_none(id=data.catalog_id, project_id=project_id)
            if catalog is None:
                raise AppException("目录不存在", 404)
        env = await TestEnvironment.create(
            project_id=project_id,
            catalog_id=data.catalog_id,
            env_name=data.env_name,
            description=data.description,
        )
        return await cls.get_detail(user, env.id)

    @classmethod
    async def copy(cls, user: User, environment_id: int, new_name: str | None = None) -> EnvironmentDetail:
        """复制变量文件（含配置项和数据库关联）。"""
        from service.test_environment.models import TestEnvironmentConfig

        source = await cls._get_or_404(environment_id)
        await ensure_project_editor(source.project_id, user)

        # 确定新名称
        base_name = new_name or f"{source.env_name}_copy"
        copy_name = base_name
        suffix = 1
        while await TestEnvironment.filter(project_id=source.project_id, env_name=copy_name).exists():
            suffix += 1
            copy_name = f"{base_name}_{suffix}"

        # 创建新环境
        new_env = await TestEnvironment.create(
            project_id=source.project_id,
            catalog_id=source.catalog_id,
            env_name=copy_name,
            description=source.description,
        )

        # 复制配置项
        configs = await TestEnvironmentConfig.filter(environment_id=environment_id).all()
        if configs:
            new_configs = [
                TestEnvironmentConfig(
                    environment_id=new_env.id,
                    config_group=c.config_group,
                    name=c.name,
                    config_type=c.config_type,
                    value=c.value,
                    remark=c.remark,
                )
                for c in configs
            ]
            await TestEnvironmentConfig.bulk_create(new_configs)

        # 复制数据库关联
        db_relations = await EnvironmentDbRelation.filter(environment_id=environment_id).all()
        if db_relations:
            new_relations = [
                EnvironmentDbRelation(
                    environment_id=new_env.id,
                    db_connection_id=r.db_connection_id,
                )
                for r in db_relations
            ]
            await EnvironmentDbRelation.bulk_create(new_relations)

        return await cls.get_detail(user, new_env.id)

    @classmethod
    async def get_detail(cls, user: User, environment_id: int) -> EnvironmentDetail:
        env = await cls._get_or_404(environment_id)
        await ensure_project_viewer(env.project_id, user)
        db_ids = await EnvironmentDbRelation.filter(environment_id=environment_id).values_list(
            "db_connection_id", flat=True
        )
        func_relations = await EnvironmentFunctionRelation.filter(
            environment_id=environment_id
        ).order_by("sort_order", "id")
        func_bindings = [
            FunctionBindItem(
                function_file_id=rel.function_file_id,
                sort_order=rel.sort_order,
            )
            for rel in func_relations
        ]
        brief = cls._to_brief(env)
        return EnvironmentDetail(
            **brief.model_dump(),
            db_connection_ids=list(db_ids),
            function_file_ids=[b.function_file_id for b in func_bindings],
            function_bindings=func_bindings,
        )

    @classmethod
    async def update(
        cls, user: User, environment_id: int, data: EnvironmentUpdateRequest
    ) -> EnvironmentDetail:
        env = await cls._get_or_404(environment_id)
        await ensure_project_editor(env.project_id, user)
        if data.env_name is not None:
            name = data.env_name.strip()
            exists = await TestEnvironment.filter(
                project_id=env.project_id, env_name=name
            ).exclude(id=environment_id).exists()
            if exists:
                raise AppException("变量文件名称已存在", 409)
            env.env_name = name
        if data.description is not None:
            env.description = data.description
        if data.catalog_id is not None:
            if data.catalog_id == 0:
                env.catalog_id = None
            else:
                catalog = await EnvCatalog.get_or_none(
                    id=data.catalog_id, project_id=env.project_id
                )
                if catalog is None:
                    raise AppException("目录不存在", 404)
                env.catalog_id = data.catalog_id
        await env.save()
        return await cls.get_detail(user, environment_id)

    @classmethod
    async def delete(cls, user: User, environment_id: int) -> None:
        env = await cls._get_or_404(environment_id)
        await ensure_project_editor(env.project_id, user)
        await env.delete()

    @staticmethod
    def _to_brief(env: TestEnvironment) -> EnvironmentBrief:
        return EnvironmentBrief(
            id=env.id,
            project_id=env.project_id,
            catalog_id=env.catalog_id,
            env_name=env.env_name,
            description=env.description,
            created_at=env.created_at,
            updated_at=env.updated_at,
        )
