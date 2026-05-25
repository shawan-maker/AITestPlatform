from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.test_environment.models import (
    EnvFunctionFile,
    EnvironmentFunctionRelation,
    TestEnvironment,
)
from service.test_environment.permissions import (
    ensure_function_file_edit,
    ensure_function_file_view,
    ensure_project_editor,
    ensure_project_viewer,
)
from service.test_environment.function.schemas import (
    EnvironmentFunctionBindRequest,
    FunctionFileBrief,
    FunctionFileCreateRequest,
    FunctionFileDetail,
    FunctionFileUpdateRequest,
    PaginatedFunctionFiles,
)
from service.user.models import User


class FunctionFileService:
    @classmethod
    def _validate_source_code(cls, source_code: str, file_name: str) -> None:
        try:
            compile(source_code, file_name, "exec")
        except SyntaxError as exc:
            raise AppException(
                f"Python 语法错误: {exc.msg} (line {exc.lineno})", 400
            ) from exc

    @classmethod
    async def validate_source(cls, file_name: str, source_code: str) -> dict:
        cls._validate_source_code(source_code, file_name)
        return {"valid": True, "file_name": file_name}

    @classmethod
    async def _get_or_404(cls, file_id: int) -> EnvFunctionFile:
        func = await EnvFunctionFile.get_or_none(id=file_id)
        if func is None:
            raise AppException("函数文件不存在", 404)
        return func

    @classmethod
    async def _sync_project_id(cls, file_id: int) -> None:
        func = await EnvFunctionFile.get(id=file_id)
        relations = await EnvironmentFunctionRelation.filter(
            function_file_id=file_id
        ).prefetch_related("environment")
        if not relations:
            func.project_id = None
        else:
            func.project_id = relations[0].environment.project_id
        await func.save()

    @classmethod
    async def list_files(
        cls,
        user: User,
        *,
        project_id: int | None = None,
        bound: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedFunctionFiles:
        if bound is False:
            qs = EnvFunctionFile.filter(project_id__isnull=True)
            if not user.is_super_admin:
                qs = qs.filter(created_by_id=user.id)
        elif project_id is not None:
            await ensure_project_viewer(project_id, user)
            if bound is True:
                env_ids = await TestEnvironment.filter(project_id=project_id).values_list(
                    "id", flat=True
                )
                file_ids = await EnvironmentFunctionRelation.filter(
                    environment_id__in=list(env_ids)
                ).values_list("function_file_id", flat=True)
                qs = EnvFunctionFile.filter(id__in=list(set(file_ids)))
            else:
                qs = EnvFunctionFile.filter(project_id=project_id)
        else:
            if not user.is_super_admin:
                raise AppException("请指定 project_id 或 bound=false", 400)
            qs = EnvFunctionFile.all()
        qs = qs.order_by("-updated_at")
        total, items = await paginate(qs, page, page_size)
        briefs = []
        for func in items:
            is_bound = await EnvironmentFunctionRelation.filter(
                function_file_id=func.id
            ).exists()
            briefs.append(cls._to_brief(func, is_bound))
        return PaginatedFunctionFiles(
            total=total, page=page, page_size=page_size, items=briefs
        )

    @classmethod
    async def create(cls, user: User, data: FunctionFileCreateRequest) -> FunctionFileDetail:
        cls._validate_source_code(data.source_code, data.file_name)
        if await EnvFunctionFile.filter(file_name=data.file_name).exists():
            raise AppException("函数文件名已存在", 409)
        func = await EnvFunctionFile.create(
            file_name=data.file_name,
            source_code=data.source_code,
            created_by_id=user.id,
        )
        if data.environment_ids:
            for env_id in data.environment_ids:
                env = await TestEnvironment.get_or_none(id=env_id)
                if env is None:
                    raise AppException(f"变量文件 {env_id} 不存在", 404)
                await ensure_project_editor(env.project_id, user)
                await EnvironmentFunctionRelation.get_or_create(
                    environment_id=env_id,
                    function_file_id=func.id,
                    defaults={"sort_order": 0},
                )
            await cls._sync_project_id(func.id)
            func = await cls._get_or_404(func.id)
        is_bound = await EnvironmentFunctionRelation.filter(function_file_id=func.id).exists()
        return cls._to_detail(func, is_bound)

    @classmethod
    async def get_detail(cls, user: User, file_id: int) -> FunctionFileDetail:
        func = await cls._get_or_404(file_id)
        await ensure_function_file_view(func, user)
        is_bound = await EnvironmentFunctionRelation.filter(function_file_id=func.id).exists()
        return cls._to_detail(func, is_bound)

    @classmethod
    async def update(
        cls, user: User, file_id: int, data: FunctionFileUpdateRequest
    ) -> FunctionFileDetail:
        func = await cls._get_or_404(file_id)
        await ensure_function_file_edit(func, user)
        if data.file_name is not None:
            exists = await EnvFunctionFile.filter(file_name=data.file_name).exclude(
                id=file_id
            ).exists()
            if exists:
                raise AppException("函数文件名已存在", 409)
            func.file_name = data.file_name
        if data.source_code is not None:
            cls._validate_source_code(data.source_code, func.file_name)
            func.source_code = data.source_code
        await func.save()
        is_bound = await EnvironmentFunctionRelation.filter(function_file_id=func.id).exists()
        return cls._to_detail(func, is_bound)

    @classmethod
    async def delete(cls, user: User, file_id: int) -> None:
        func = await cls._get_or_404(file_id)
        await ensure_function_file_edit(func, user)
        await func.delete()

    @classmethod
    async def bind_to_environment(
        cls, user: User, environment_id: int, data: EnvironmentFunctionBindRequest
    ) -> list[dict]:
        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise AppException("变量文件不存在", 404)
        await ensure_project_editor(env.project_id, user)
        for item in data.items:
            if not await EnvFunctionFile.filter(id=item.function_file_id).exists():
                raise AppException(f"函数文件 {item.function_file_id} 不存在", 404)
        await EnvironmentFunctionRelation.filter(environment_id=environment_id).delete()
        for item in data.items:
            await EnvironmentFunctionRelation.create(
                environment_id=environment_id,
                function_file_id=item.function_file_id,
                sort_order=item.sort_order,
            )
            await cls._sync_project_id(item.function_file_id)
        return [{"function_file_id": i.function_file_id, "sort_order": i.sort_order} for i in data.items]

    @staticmethod
    def _to_brief(func: EnvFunctionFile, is_bound: bool) -> FunctionFileBrief:
        return FunctionFileBrief(
            id=func.id,
            file_name=func.file_name,
            project_id=func.project_id,
            created_by_id=func.created_by_id,
            is_bound=is_bound,
            created_at=func.created_at,
            updated_at=func.updated_at,
        )

    @staticmethod
    def _to_detail(func: EnvFunctionFile, is_bound: bool) -> FunctionFileDetail:
        brief = FunctionFileService._to_brief(func, is_bound)
        return FunctionFileDetail(**brief.model_dump(), source_code=func.source_code)
