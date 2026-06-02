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
    BoundEnvironmentOption,
    EnvironmentFunctionBindRequest,
    FunctionDebugRequest,
    FunctionDebugResult,
    FunctionFileBrief,
    FunctionFileCreateRequest,
    FunctionFileDetail,
    FunctionFileUpdateRequest,
    PaginatedFunctionFiles,
)
from service.test_environment.function.sandbox import (
    execute_function,
    method_name_matches,
    params_have_var_refs,
    parse_method_names,
    source_has_var_refs,
)
from service.test_environment.variable.assembler import TestEnvDataAssembler
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
        keyword: str | None = None,
        method_name: str | None = None,
        environment_id: int | None = None,
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
        if keyword:
            qs = qs.filter(file_name__icontains=keyword.strip())
        if method_name and method_name.strip():
            qs = await cls._filter_queryset_by_method_name(qs, method_name)
        if environment_id is not None:
            bound_file_ids = await EnvironmentFunctionRelation.filter(
                environment_id=environment_id
            ).values_list("function_file_id", flat=True)
            qs = qs.filter(id__in=list(bound_file_ids) or [-1])
        qs = qs.order_by("-updated_at")
        total, items = await paginate(qs, page, page_size)
        bindings = await cls._bindings_for_files([func.id for func in items])
        briefs = []
        for func in items:
            is_bound = func.id in bindings
            env_ids, env_names = bindings.get(func.id, ([], []))
            briefs.append(cls._to_brief(func, is_bound, env_ids, env_names))
        return PaginatedFunctionFiles(
            total=total, page=page, page_size=page_size, items=briefs
        )

    @classmethod
    async def _filter_queryset_by_method_name(cls, qs, method_name: str):
        rows = await qs.only("id", "source_code")
        matching_ids = [
            row.id for row in rows if method_name_matches(row.source_code, method_name)
        ]
        if not matching_ids:
            return EnvFunctionFile.filter(id__in=[-1])
        return EnvFunctionFile.filter(id__in=matching_ids)

    @classmethod
    async def list_bound_environment_options(
        cls, user: User, project_id: int
    ) -> list[BoundEnvironmentOption]:
        await ensure_project_viewer(project_id, user)
        project_env_ids = await TestEnvironment.filter(project_id=project_id).values_list(
            "id", flat=True
        )
        if not project_env_ids:
            return []
        relation_env_ids = await EnvironmentFunctionRelation.filter(
            environment_id__in=list(project_env_ids)
        ).values_list("environment_id", flat=True)
        unique_ids = sorted(set(relation_env_ids))
        if not unique_ids:
            return []
        envs = await TestEnvironment.filter(id__in=unique_ids).order_by("env_name")
        return [BoundEnvironmentOption(id=e.id, env_name=e.env_name) for e in envs]

    @classmethod
    async def create(
        cls,
        user: User,
        data: FunctionFileCreateRequest,
        *,
        project_id: int | None = None,
    ) -> FunctionFileDetail:
        cls._validate_source_code(data.source_code, data.file_name)
        if await EnvFunctionFile.filter(file_name=data.file_name).exists():
            raise AppException("函数文件名已存在", 409)
        if data.environment_ids:
            for env_id in data.environment_ids:
                env = await TestEnvironment.get_or_none(id=env_id)
                if env is None:
                    raise AppException(f"变量文件 {env_id} 不存在", 404)
                await ensure_project_editor(env.project_id, user)
        elif project_id is not None:
            await ensure_project_editor(project_id, user)
        initial_project_id = None if data.environment_ids else project_id
        func = await EnvFunctionFile.create(
            file_name=data.file_name,
            source_code=data.source_code,
            created_by_id=user.id,
            project_id=initial_project_id,
        )
        if data.environment_ids:
            for env_id in data.environment_ids:
                await EnvironmentFunctionRelation.get_or_create(
                    environment_id=env_id,
                    function_file_id=func.id,
                    defaults={"sort_order": 0},
                )
            await cls._sync_project_id(func.id)
            func = await cls._get_or_404(func.id)
        is_bound = await EnvironmentFunctionRelation.filter(function_file_id=func.id).exists()
        env_ids, env_names = await cls._environment_names_for(func.id)
        return await cls._to_detail(func, is_bound, env_ids, env_names)

    @classmethod
    async def get_detail(cls, user: User, file_id: int) -> FunctionFileDetail:
        func = await cls._get_or_404(file_id)
        await ensure_function_file_view(func, user)
        is_bound = await EnvironmentFunctionRelation.filter(function_file_id=func.id).exists()
        env_ids, env_names = await cls._environment_names_for(func.id)
        return await cls._to_detail(func, is_bound, env_ids, env_names)

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
        if data.environment_ids is not None:
            await cls._sync_environment_bindings(user, func, data.environment_ids)
        await func.save()
        is_bound = await EnvironmentFunctionRelation.filter(function_file_id=func.id).exists()
        env_ids, env_names = await cls._environment_names_for(func.id)
        return await cls._to_detail(func, is_bound, env_ids, env_names)

    @classmethod
    async def _sync_environment_bindings(
        cls, user: User, func: EnvFunctionFile, environment_ids: list[int]
    ) -> None:
        for env_id in environment_ids:
            env = await TestEnvironment.get_or_none(id=env_id)
            if env is None:
                raise AppException(f"变量文件 {env_id} 不存在", 404)
            await ensure_project_editor(env.project_id, user)
        await EnvironmentFunctionRelation.filter(function_file_id=func.id).delete()
        for env_id in environment_ids:
            await EnvironmentFunctionRelation.create(
                environment_id=env_id,
                function_file_id=func.id,
                sort_order=0,
            )
        await cls._sync_project_id(func.id)
        refreshed = await cls._get_or_404(func.id)
        func.project_id = refreshed.project_id

    @classmethod
    async def debug(
        cls, user: User, file_id: int, data: FunctionDebugRequest
    ) -> FunctionDebugResult:
        func = await cls._get_or_404(file_id)
        await ensure_function_file_view(func, user)
        source = func.source_code
        needs_env = source_has_var_refs(source) or params_have_var_refs(data.params)
        if needs_env and data.environment_id is None:
            raise AppException(
                "代码或参数使用了 $变量 引用，请选择变量文件（environment_id）", 400
            )
        envs: dict[str, str] = {}
        if data.environment_id is not None:
            env = await TestEnvironment.get_or_none(id=data.environment_id)
            if env is None:
                raise AppException("变量文件不存在", 404)
            await ensure_project_viewer(env.project_id, user)
            envs = await TestEnvDataAssembler.merge_persisted_envs(
                env.project_id, data.environment_id
            )
        merged_envs = {**envs}
        for key, value in data.params.items():
            if not (isinstance(value, str) and value.startswith("$")):
                merged_envs[key] = str(value) if value is not None else ""
        try:
            result, stdout, stderr, duration_ms = execute_function(
                source,
                func.file_name,
                data.method_name,
                data.params,
                merged_envs,
            )
            error_text = stderr.strip()
            return FunctionDebugResult(
                success=True,
                result=result,
                print_out=stdout,
                error=error_text,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            return FunctionDebugResult(
                success=False,
                error=str(exc),
            )

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

    @classmethod
    async def _bindings_for_files(
        cls, file_ids: list[int]
    ) -> dict[int, tuple[list[int], list[str]]]:
        if not file_ids:
            return {}
        relations = await EnvironmentFunctionRelation.filter(
            function_file_id__in=file_ids
        ).prefetch_related("environment")
        result: dict[int, tuple[list[int], list[str]]] = {}
        for rel in relations:
            env_ids, env_names = result.setdefault(rel.function_file_id, ([], []))
            env_ids.append(rel.environment_id)
            env_names.append(rel.environment.env_name)
        return result

    @classmethod
    async def _environment_names_for(cls, func_id: int) -> tuple[list[int], list[str]]:
        bindings = await cls._bindings_for_files([func_id])
        return bindings.get(func_id, ([], []))

    @staticmethod
    def _to_brief(
        func: EnvFunctionFile,
        is_bound: bool,
        environment_ids: list[int] | None = None,
        environment_names: list[str] | None = None,
    ) -> FunctionFileBrief:
        env_ids = environment_ids or []
        env_names = environment_names or []
        return FunctionFileBrief(
            id=func.id,
            file_name=func.file_name,
            project_id=func.project_id,
            created_by_id=func.created_by_id,
            is_bound=is_bound,
            method_names=parse_method_names(func.source_code),
            environment_ids=env_ids,
            environment_names=env_names,
            created_at=func.created_at,
            updated_at=func.updated_at,
        )

    @classmethod
    async def _to_detail(
        cls,
        func: EnvFunctionFile,
        is_bound: bool,
        environment_ids: list[int] | None = None,
        environment_names: list[str] | None = None,
    ) -> FunctionFileDetail:
        if environment_ids is None or environment_names is None:
            environment_ids, environment_names = await cls._environment_names_for(func.id)
        brief = FunctionFileService._to_brief(
            func, is_bound, environment_ids, environment_names
        )
        return FunctionFileDetail(**brief.model_dump(), source_code=func.source_code)
