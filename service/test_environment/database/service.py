import asyncmy
from copy import deepcopy

from service.core.enums import DbType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.core.secret_crypto import decrypt_secret, encrypt_secret
from service.test_environment.models import (
    DbConnection,
    DbConnectionTestLog,
    EnvironmentDbRelation,
    TestEnvironment,
)
from service.test_environment.permissions import (
    ensure_db_connection_edit,
    ensure_db_connection_view,
    ensure_project_editor,
    ensure_project_viewer,
)
from service.test_environment.database.schemas import (
    DbConnectionBrief,
    DbConnectionCreateRequest,
    DbConnectionDetail,
    DbConnectionTestLogOut,
    DbConnectionTestResult,
    DbConnectionUpdateRequest,
    EnvironmentDbBindRequest,
    PaginatedDbConnections,
    PaginatedDbTestLogs,
)
from service.user.models import User


class DbConnectionService:
    @classmethod
    def _mask_config(cls, config: dict) -> dict:
        result = deepcopy(config or {})
        if result.get("password"):
            result["password"] = "***"
        return result

    @classmethod
    def _prepare_config_for_storage(cls, config_input, existing: dict | None = None) -> dict:
        data = config_input.model_dump()
        pwd = data.pop("password", None)
        if pwd:
            data["password"] = encrypt_secret(pwd)
        elif existing and existing.get("password"):
            data["password"] = existing["password"]
        else:
            data["password"] = ""
        return data

    @classmethod
    async def _get_or_404(cls, connection_id: int) -> DbConnection:
        conn = await DbConnection.get_or_none(id=connection_id)
        if conn is None:
            raise AppException("数据库连接不存在", 404)
        return conn

    @classmethod
    async def _sync_project_id(cls, connection_id: int) -> None:
        conn = await DbConnection.get(id=connection_id)
        relations = await EnvironmentDbRelation.filter(
            db_connection_id=connection_id
        ).prefetch_related("environment")
        if not relations:
            conn.project_id = None
        else:
            conn.project_id = relations[0].environment.project_id
        await conn.save()

    @classmethod
    async def _validate_server_names_unique(cls, environment_id: int, connection_ids: list[int]) -> None:
        if not connection_ids:
            return
        connections = await DbConnection.filter(id__in=connection_ids)
        names = [c.server_name for c in connections]
        if len(names) != len(set(names)):
            raise AppException("同一变量文件绑定的 server_name 不得重复", 400)

    @classmethod
    async def list_connections(
        cls,
        user: User,
        *,
        project_id: int | None = None,
        bound: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedDbConnections:
        if bound is False:
            qs = DbConnection.filter(project_id__isnull=True)
            if not user.is_super_admin:
                qs = qs.filter(created_by_id=user.id)
        elif project_id is not None:
            await ensure_project_viewer(project_id, user)
            if bound is True:
                env_ids = await TestEnvironment.filter(project_id=project_id).values_list(
                    "id", flat=True
                )
                conn_ids = await EnvironmentDbRelation.filter(
                    environment_id__in=list(env_ids)
                ).values_list("db_connection_id", flat=True)
                qs = DbConnection.filter(id__in=list(set(conn_ids)))
            else:
                qs = DbConnection.filter(project_id=project_id)
        else:
            if not user.is_super_admin:
                raise AppException("请指定 project_id 或 bound=false", 400)
            qs = DbConnection.all()
        if keyword:
            qs = qs.filter(connection_name__icontains=keyword.strip())
        qs = qs.order_by("-updated_at")
        total, items = await paginate(qs, page, page_size)
        briefs = []
        for conn in items:
            is_bound = await EnvironmentDbRelation.filter(db_connection_id=conn.id).exists()
            briefs.append(cls._to_brief(conn, is_bound))
        return PaginatedDbConnections(
            total=total, page=page, page_size=page_size, items=briefs
        )

    @classmethod
    async def create(cls, user: User, data: DbConnectionCreateRequest) -> DbConnectionDetail:
        if await DbConnection.filter(connection_name=data.connection_name).exists():
            raise AppException("连接名称已存在", 409)
        config = cls._prepare_config_for_storage(data.config)
        conn = await DbConnection.create(
            connection_name=data.connection_name,
            server_name=data.server_name,
            db_type=data.db_type,
            config=config,
            description=data.description,
            created_by_id=user.id,
        )
        if data.environment_ids:
            for env_id in data.environment_ids:
                env = await TestEnvironment.get_or_none(id=env_id)
                if env is None:
                    raise AppException(f"变量文件 {env_id} 不存在", 404)
                await ensure_project_editor(env.project_id, user)
            for env_id in data.environment_ids:
                existing_ids = list(
                    await EnvironmentDbRelation.filter(environment_id=env_id).values_list(
                        "db_connection_id", flat=True
                    )
                )
                combined = list(set(existing_ids) | {conn.id})
                await cls._validate_server_names_unique(env_id, combined)
                await EnvironmentDbRelation.get_or_create(
                    environment_id=env_id, db_connection_id=conn.id
                )
            await cls._sync_project_id(conn.id)
            conn = await cls._get_or_404(conn.id)
        return cls._to_detail(conn, await EnvironmentDbRelation.filter(db_connection_id=conn.id).exists())

    @classmethod
    async def get_detail(cls, user: User, connection_id: int) -> DbConnectionDetail:
        conn = await cls._get_or_404(connection_id)
        await ensure_db_connection_view(conn, user)
        is_bound = await EnvironmentDbRelation.filter(db_connection_id=conn.id).exists()
        return cls._to_detail(conn, is_bound)

    @classmethod
    async def update(
        cls, user: User, connection_id: int, data: DbConnectionUpdateRequest
    ) -> DbConnectionDetail:
        conn = await cls._get_or_404(connection_id)
        await ensure_db_connection_edit(conn, user)
        if data.connection_name is not None:
            exists = await DbConnection.filter(connection_name=data.connection_name).exclude(
                id=connection_id
            ).exists()
            if exists:
                raise AppException("连接名称已存在", 409)
            conn.connection_name = data.connection_name
        if data.server_name is not None:
            conn.server_name = data.server_name
        if data.db_type is not None:
            conn.db_type = data.db_type
        if data.config is not None:
            conn.config = cls._prepare_config_for_storage(data.config, conn.config)
        if data.description is not None:
            conn.description = data.description
        await conn.save()
        is_bound = await EnvironmentDbRelation.filter(db_connection_id=conn.id).exists()
        return cls._to_detail(conn, is_bound)

    @classmethod
    async def delete(cls, user: User, connection_id: int) -> None:
        conn = await cls._get_or_404(connection_id)
        await ensure_db_connection_edit(conn, user)
        await conn.delete()

    @classmethod
    async def bind_to_environment(
        cls, user: User, environment_id: int, data: EnvironmentDbBindRequest
    ) -> list[int]:
        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise AppException("变量文件不存在", 404)
        await ensure_project_editor(env.project_id, user)
        await cls._validate_server_names_unique(environment_id, data.db_connection_ids)
        for cid in data.db_connection_ids:
            if not await DbConnection.filter(id=cid).exists():
                raise AppException(f"数据库连接 {cid} 不存在", 404)
        await EnvironmentDbRelation.filter(environment_id=environment_id).delete()
        for cid in data.db_connection_ids:
            await EnvironmentDbRelation.create(environment_id=environment_id, db_connection_id=cid)
            await cls._sync_project_id(cid)
        return data.db_connection_ids

    @classmethod
    async def _get_plain_password(cls, config: dict) -> str:
        pwd = config.get("password") or ""
        if not pwd:
            return ""
        try:
            return decrypt_secret(pwd)
        except Exception:
            return pwd

    @classmethod
    async def _test_mysql(cls, config: dict) -> tuple[bool, str]:
        host = config.get("host")
        port = int(config.get("port", 3306))
        user = config.get("username") or config.get("user")
        password = await cls._get_plain_password(config)
        database = config.get("database_name") or config.get("database")
        try:
            conn = await asyncmy.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                db=database or "",
            )
            try:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
            finally:
                conn.close()
            return True, "连接成功"
        except Exception as exc:
            return False, str(exc)

    @classmethod
    async def test_connection(cls, user: User, connection_id: int) -> DbConnectionTestResult:
        conn = await cls._get_or_404(connection_id)
        await ensure_db_connection_edit(conn, user)
        if conn.db_type == DbType.mysql:
            success, message = await cls._test_mysql(conn.config or {})
        else:
            success, message = False, f"暂不支持 {conn.db_type.value} 连接测试"
        log = await DbConnectionTestLog.create(
            db_connection_id=connection_id,
            success=success,
            message=message,
            tested_by_id=user.id,
        )
        return DbConnectionTestResult(
            success=success, message=message, tested_at=log.tested_at
        )

    @classmethod
    async def list_test_logs(
        cls, user: User, connection_id: int, page: int = 1, page_size: int = 20
    ) -> PaginatedDbTestLogs:
        conn = await cls._get_or_404(connection_id)
        await ensure_db_connection_view(conn, user)
        qs = DbConnectionTestLog.filter(db_connection_id=connection_id).order_by("-tested_at")
        total, items = await paginate(qs, page, page_size)
        return PaginatedDbTestLogs(
            total=total,
            page=page,
            page_size=page_size,
            items=[
                DbConnectionTestLogOut(
                    id=log.id,
                    success=log.success,
                    message=log.message,
                    tested_by_id=log.tested_by_id,
                    tested_at=log.tested_at,
                )
                for log in items
            ],
        )

    @classmethod
    def _to_brief(cls, conn: DbConnection, is_bound: bool) -> DbConnectionBrief:
        return DbConnectionBrief(
            id=conn.id,
            connection_name=conn.connection_name,
            server_name=conn.server_name,
            db_type=conn.db_type,
            description=conn.description,
            project_id=conn.project_id,
            created_by_id=conn.created_by_id,
            is_bound=is_bound,
            created_at=conn.created_at,
            updated_at=conn.updated_at,
        )

    @classmethod
    def _to_detail(cls, conn: DbConnection, is_bound: bool) -> DbConnectionDetail:
        brief = cls._to_brief(conn, is_bound)
        return DbConnectionDetail(
            **brief.model_dump(),
            config=cls._mask_config(conn.config or {}),
        )
