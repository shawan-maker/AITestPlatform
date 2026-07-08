"""测试环境管理模块 - variable/import_export_service

业务逻辑服务
"""
from service.core.exceptions import AppException
from service.test_environment.database.service import DbConnectionService
from service.test_environment.variable.config_service import EnvironmentConfigService
from service.test_environment.variable.environment_service import EnvironmentService
from service.test_environment.function.service import FunctionFileService
from service.test_environment.models import (
    DbConnection,
    EnvFunctionFile,
    EnvironmentDbRelation,
    EnvironmentFunctionRelation,
    TestEnvironment,
    TestEnvironmentConfig,
)
from service.test_environment.permissions import ensure_project_editor
from service.test_environment.database.schemas import (
    DbConnectionConfigInput,
    DbConnectionCreateRequest,
    EnvironmentDbBindRequest,
    ExportDbConnectionEmbed,
)
from service.test_environment.function.schemas import (
    EnvironmentFunctionBindRequest,
    ExportFunctionEmbed,
    FunctionBindItem,
    FunctionFileCreateRequest,
)
from service.test_environment.variable.schemas import (
    ConfigItemCreateRequest,
    EnvironmentCreateRequest,
    EnvironmentExportBundle,
    EnvironmentImportRequest,
)
from service.user.models import User


class ImportExportService:
    @classmethod
    async def export_environment(cls, user: User, environment_id: int) -> EnvironmentExportBundle:
        detail = await EnvironmentService.get_detail(user, environment_id)
        configs = await EnvironmentConfigService.list_configs(user, environment_id)
        func_relations = await EnvironmentFunctionRelation.filter(
            environment_id=environment_id
        ).prefetch_related("function_file").order_by("sort_order", "id")
        bindings: list[FunctionBindItem] = []
        functions: list[ExportFunctionEmbed] = []
        seen_names: set[str] = set()
        for rel in func_relations:
            func = rel.function_file
            bindings.append(
                FunctionBindItem(
                    function_file_id=rel.function_file_id,
                    sort_order=rel.sort_order,
                    file_name=func.file_name,
                )
            )
            if func.file_name not in seen_names:
                seen_names.add(func.file_name)
                functions.append(
                    ExportFunctionEmbed(
                        file_name=func.file_name, source_code=func.source_code
                    )
                )

        db_relations = await EnvironmentDbRelation.filter(
            environment_id=environment_id
        ).prefetch_related("db_connection").order_by("id")
        db_connections: list[ExportDbConnectionEmbed] = []
        for rel in db_relations:
            conn = rel.db_connection
            masked = DbConnectionService._mask_config(conn.config or {})
            db_connections.append(
                ExportDbConnectionEmbed(
                    connection_name=conn.connection_name,
                    server_name=conn.server_name,
                    db_type=conn.db_type,
                    config=DbConnectionConfigInput(
                        host=masked.get("host", ""),
                        port=int(masked.get("port", 3306)),
                        username=masked.get("username") or masked.get("user") or "",
                        password=masked.get("password"),
                        database_name=masked.get("database_name") or masked.get("database"),
                    ),
                    description=conn.description,
                )
            )

        return EnvironmentExportBundle(
            env_name=detail.env_name,
            description=detail.description,
            catalog_id=detail.catalog_id,
            import_mode="embed",
            configs=configs,
            db_connection_ids=detail.db_connection_ids,
            db_connections=db_connections,
            function_bindings=bindings,
            functions=functions,
        )

    @classmethod
    async def _resolve_import_mode(cls, data: EnvironmentImportRequest) -> str:
        return data.import_mode or data.bundle.import_mode or "reference"

    @classmethod
    async def _import_db_connections(
        cls,
        user: User,
        env_id: int,
        bundle: EnvironmentExportBundle,
        import_mode: str,
    ) -> None:
        db_ids: list[int] = []
        if import_mode == "embed" and bundle.db_connections:
            for db_def in bundle.db_connections:
                conn_id = await cls._create_or_get_db_connection(user, env_id, db_def)
                db_ids.append(conn_id)
        elif bundle.db_connection_ids:
            for cid in bundle.db_connection_ids:
                if await DbConnection.filter(id=cid).exists():
                    db_ids.append(cid)
                elif import_mode == "reference":
                    embed = cls._find_db_embed(bundle, cid)
                    if embed:
                        conn_id = await cls._create_or_get_db_connection(user, env_id, embed)
                        db_ids.append(conn_id)
            if not db_ids and bundle.db_connections:
                for db_def in bundle.db_connections:
                    conn_id = await cls._create_or_get_db_connection(user, env_id, db_def)
                    db_ids.append(conn_id)
        elif bundle.db_connections:
            for db_def in bundle.db_connections:
                conn_id = await cls._create_or_get_db_connection(user, env_id, db_def)
                db_ids.append(conn_id)

        if db_ids:
            await DbConnectionService.bind_to_environment(
                user, env_id, EnvironmentDbBindRequest(db_connection_ids=db_ids)
            )

    @classmethod
    def _find_db_embed(
        cls, bundle: EnvironmentExportBundle, connection_id: int
    ) -> ExportDbConnectionEmbed | None:
        try:
            idx = bundle.db_connection_ids.index(connection_id)
        except ValueError:
            return None
        if idx < len(bundle.db_connections):
            return bundle.db_connections[idx]
        return None

    @classmethod
    async def _create_or_get_db_connection(
        cls, user: User, env_id: int, db_def: ExportDbConnectionEmbed
    ) -> int:
        existing = await DbConnection.get_or_none(connection_name=db_def.connection_name)
        if existing:
            await EnvironmentDbRelation.get_or_create(
                environment_id=env_id, db_connection_id=existing.id
            )
            await DbConnectionService._sync_project_id(existing.id)
            return existing.id
        pwd = db_def.config.password
        if pwd == "***":
            pwd = None
        detail = await DbConnectionService.create(
            user,
            DbConnectionCreateRequest(
                connection_name=db_def.connection_name,
                server_name=db_def.server_name,
                db_type=db_def.db_type,
                config=DbConnectionConfigInput(
                    host=db_def.config.host,
                    port=db_def.config.port,
                    username=db_def.config.username,
                    password=pwd,
                    database_name=db_def.config.database_name,
                ),
                description=db_def.description,
                environment_ids=[env_id],
            ),
        )
        return detail.id

    @classmethod
    async def _import_functions(
        cls,
        user: User,
        env_id: int,
        bundle: EnvironmentExportBundle,
        import_mode: str,
    ) -> None:
        if not bundle.function_bindings and not bundle.functions:
            return

        file_name_to_id: dict[str, int] = {}
        if import_mode == "embed" or bundle.functions:
            for fn in bundle.functions:
                file_name_to_id[fn.file_name] = await cls._create_or_get_function(
                    user, fn
                )

        new_bindings: list[FunctionBindItem] = []
        if import_mode == "embed" and bundle.function_bindings:
            for binding in bundle.function_bindings:
                fname = binding.file_name
                if not fname and bundle.functions:
                    continue
                if fname and fname in file_name_to_id:
                    new_bindings.append(
                        FunctionBindItem(
                            function_file_id=file_name_to_id[fname],
                            sort_order=binding.sort_order,
                        )
                    )
        elif import_mode == "reference" and bundle.function_bindings:
            for binding in bundle.function_bindings:
                if await EnvFunctionFile.filter(id=binding.function_file_id).exists():
                    new_bindings.append(
                        FunctionBindItem(
                            function_file_id=binding.function_file_id,
                            sort_order=binding.sort_order,
                        )
                    )
                elif binding.file_name and binding.file_name in file_name_to_id:
                    new_bindings.append(
                        FunctionBindItem(
                            function_file_id=file_name_to_id[binding.file_name],
                            sort_order=binding.sort_order,
                        )
                    )
                else:
                    embed = next(
                        (f for f in bundle.functions if f.file_name == binding.file_name),
                        None,
                    )
                    if embed:
                        fid = await cls._create_or_get_function(user, embed)
                        file_name_to_id[embed.file_name] = fid
                        new_bindings.append(
                            FunctionBindItem(
                                function_file_id=fid, sort_order=binding.sort_order
                            )
                        )

        if new_bindings:
            await FunctionFileService.bind_to_environment(
                user,
                env_id,
                EnvironmentFunctionBindRequest(items=new_bindings),
            )

    @classmethod
    async def _create_or_get_function(
        cls, user: User, fn: ExportFunctionEmbed
    ) -> int:
        existing = await EnvFunctionFile.get_or_none(file_name=fn.file_name)
        if existing:
            return existing.id
        detail = await FunctionFileService.create(
            user,
            FunctionFileCreateRequest(
                file_name=fn.file_name, source_code=fn.source_code
            ),
        )
        return detail.id

    @classmethod
    async def import_environment(
        cls, user: User, project_id: int, data: EnvironmentImportRequest
    ) -> dict:
        await ensure_project_editor(project_id, user)
        bundle = data.bundle
        import_mode = await cls._resolve_import_mode(data)
        existing = await TestEnvironment.get_or_none(
            project_id=project_id, env_name=bundle.env_name
        )
        if existing and not data.overwrite:
            raise AppException("变量文件已存在，请设置 overwrite=true 覆盖", 409)
        if existing and data.overwrite:
            await existing.delete()

        env_detail = await EnvironmentService.create(
            user,
            project_id,
            EnvironmentCreateRequest(
                env_name=bundle.env_name,
                description=bundle.description,
                catalog_id=bundle.catalog_id,
            ),
        )
        env_id = env_detail.id
        await TestEnvironmentConfig.filter(environment_id=env_id).delete()
        for cfg in bundle.configs:
            await EnvironmentConfigService.create_item(
                user,
                env_id,
                ConfigItemCreateRequest(
                    config_group=cfg.config_group,
                    name=cfg.name,
                    config_type=cfg.config_type,
                    value=cfg.value if cfg.value != "***" else None,
                    remark=cfg.remark,
                ),
            )

        await cls._import_db_connections(user, env_id, bundle, import_mode)
        await cls._import_functions(user, env_id, bundle, import_mode)
        return {"environment_id": env_id, "env_name": bundle.env_name}
