from service.core.enums import ConfigType
from service.core.exceptions import AppException
from service.core.secret_crypto import encrypt_secret
from service.test_environment.models import TestEnvironmentConfig
from service.test_environment.permissions import ensure_project_editor, ensure_project_viewer
from service.test_environment.variable.schemas import (
    ConfigGroupReplaceRequest,
    ConfigItemCreateRequest,
    ConfigItemOut,
    ConfigItemUpdateRequest,
)
from service.user.models import User


class EnvironmentConfigService:
    ALLOWED_GROUPS = {"base", "headers", "envs"}

    @classmethod
    def _encrypt_if_needed(cls, config_type: ConfigType, value: str | None) -> str | None:
        if value is None:
            return None
        if config_type == ConfigType.secret:
            return encrypt_secret(value)
        return value

    @classmethod
    def _mask_for_response(cls, config_type: ConfigType, value: str | None) -> str | None:
        if config_type == ConfigType.secret and value:
            return "***"
        return value

    @classmethod
    async def _get_env_project_id(cls, environment_id: int) -> int:
        from service.test_environment.models import TestEnvironment

        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise AppException("变量文件不存在", 404)
        return env.project_id

    @classmethod
    async def list_configs(
        cls,
        user: User,
        environment_id: int,
        config_group: str | None = None,
    ) -> list[ConfigItemOut]:
        project_id = await cls._get_env_project_id(environment_id)
        await ensure_project_viewer(project_id, user)
        qs = TestEnvironmentConfig.filter(environment_id=environment_id)
        if config_group:
            qs = qs.filter(config_group=config_group)
        configs = await qs.order_by("config_group", "name")
        return [cls._to_out(c) for c in configs]

    @classmethod
    async def create_item(
        cls, user: User, environment_id: int, data: ConfigItemCreateRequest
    ) -> ConfigItemOut:
        if data.config_group not in cls.ALLOWED_GROUPS:
            raise AppException("不支持的 config_group", 400)
        project_id = await cls._get_env_project_id(environment_id)
        await ensure_project_editor(project_id, user)
        exists = await TestEnvironmentConfig.filter(
            environment_id=environment_id,
            config_group=data.config_group,
            name=data.name,
        ).exists()
        if exists:
            raise AppException("配置项已存在", 409)
        config = await TestEnvironmentConfig.create(
            environment_id=environment_id,
            config_group=data.config_group,
            name=data.name,
            config_type=data.config_type,
            value=cls._encrypt_if_needed(data.config_type, data.value),
            remark=data.remark,
        )
        return cls._to_out(config)

    @classmethod
    async def replace_group(
        cls,
        user: User,
        environment_id: int,
        config_group: str,
        data: ConfigGroupReplaceRequest,
    ) -> list[ConfigItemOut]:
        if config_group not in cls.ALLOWED_GROUPS:
            raise AppException("不支持的 config_group", 400)
        project_id = await cls._get_env_project_id(environment_id)
        await ensure_project_editor(project_id, user)
        await TestEnvironmentConfig.filter(
            environment_id=environment_id, config_group=config_group
        ).delete()
        created = []
        for item in data.items:
            config = await TestEnvironmentConfig.create(
                environment_id=environment_id,
                config_group=config_group,
                name=item.name,
                config_type=item.config_type,
                value=cls._encrypt_if_needed(item.config_type, item.value),
                remark=item.remark,
            )
            created.append(cls._to_out(config))
        return created

    @classmethod
    async def update_item(
        cls, user: User, config_id: int, data: ConfigItemUpdateRequest
    ) -> ConfigItemOut:
        config = await TestEnvironmentConfig.get_or_none(id=config_id)
        if config is None:
            raise AppException("配置项不存在", 404)
        project_id = await cls._get_env_project_id(config.environment_id)
        await ensure_project_editor(project_id, user)
        if data.config_type is not None:
            config.config_type = data.config_type
        if data.value is not None:
            config.value = cls._encrypt_if_needed(config.config_type, data.value)
        if data.remark is not None:
            config.remark = data.remark
        if data.name is not None:
            existing = await TestEnvironmentConfig.get_or_none(
                environment_id=config.environment_id,
                config_group=config.config_group,
                name=data.name,
            )
            if existing and existing.id != config.id:
                raise AppException("同名配置项已存在", 400)
            config.name = data.name
        await config.save()
        return cls._to_out(config)

    @classmethod
    async def delete_item(cls, user: User, config_id: int) -> None:
        config = await TestEnvironmentConfig.get_or_none(id=config_id)
        if config is None:
            raise AppException("配置项不存在", 404)
        project_id = await cls._get_env_project_id(config.environment_id)
        await ensure_project_editor(project_id, user)
        await config.delete()

    @classmethod
    def _to_out(cls, config: TestEnvironmentConfig) -> ConfigItemOut:
        return ConfigItemOut(
            id=config.id,
            environment_id=config.environment_id,
            config_group=config.config_group,
            name=config.name,
            config_type=config.config_type,
            value=cls._mask_for_response(config.config_type, config.value),
            remark=config.remark,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
