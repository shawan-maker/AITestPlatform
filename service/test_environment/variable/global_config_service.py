import logging
from typing import Any

from service.core.enums import ConfigType
from service.core.exceptions import AppException
from service.core.secret_crypto import decrypt_secret, encrypt_secret
from service.test_environment.models import ProjectGlobalConfig
from service.test_environment.permissions import ensure_project_editor, ensure_project_viewer
from service.test_environment.variable.schemas import (
    ConfigGroupItem,
    ConfigGroupReplaceRequest,
    ConfigItemOut,
    ConfigItemUpdateRequest,
)
from service.user.models import User

logger = logging.getLogger(__name__)


class ProjectGlobalConfigService:
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
    async def list_configs(cls, user: User, project_id: int) -> list[ConfigItemOut]:
        await ensure_project_viewer(project_id, user)
        configs = await ProjectGlobalConfig.filter(project_id=project_id).order_by("name")
        return [cls._to_out(c) for c in configs]

    @classmethod
    async def replace_all(
        cls, user: User, project_id: int, data: ConfigGroupReplaceRequest
    ) -> list[ConfigItemOut]:
        await ensure_project_editor(project_id, user)
        await ProjectGlobalConfig.filter(project_id=project_id).delete()
        created = []
        for item in data.items:
            config = await ProjectGlobalConfig.create(
                project_id=project_id,
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
        config = await ProjectGlobalConfig.get_or_none(id=config_id)
        if config is None:
            raise AppException("全局变量不存在", 404)
        await ensure_project_editor(config.project_id, user)
        if data.config_type is not None:
            config.config_type = data.config_type
        if data.value is not None:
            config.value = cls._encrypt_if_needed(config.config_type, data.value)
        if data.remark is not None:
            config.remark = data.remark
        await config.save()
        return cls._to_out(config)

    @classmethod
    async def delete_item(cls, user: User, config_id: int) -> None:
        config = await ProjectGlobalConfig.get_or_none(id=config_id)
        if config is None:
            raise AppException("全局变量不存在", 404)
        await ensure_project_editor(config.project_id, user)
        await config.delete()

    @classmethod
    async def load_envs_dict(cls, project_id: int, *, decrypt: bool = True) -> dict[str, str]:
        configs = await ProjectGlobalConfig.filter(project_id=project_id)
        envs: dict[str, str] = {}
        for cfg in configs:
            val = cfg.value
            if decrypt and cfg.config_type == ConfigType.secret and val:
                try:
                    val = decrypt_secret(val)
                except Exception:
                    pass
            elif cfg.config_type == ConfigType.json and val:
                continue
            envs[cfg.name] = val or ""
        return envs

    @classmethod
    async def apply_engine_writeback(
        cls,
        project_id: int,
        debug_updates: dict[str, Any],
    ) -> None:
        """将引擎执行过程中的全局变量变更同步到数据库。

        debug_updates 约定：
        - value 非 None → 新增/更新全局变量
        - value 为 None → 删除全局变量
        """
        for key, value in debug_updates.items():
            if value is None:
                deleted = await ProjectGlobalConfig.filter(project_id=project_id, name=key).delete()
                if not deleted:
                    logger.info("del_global_variable no-op: key '%s' not in project global layer", key)
            else:
                await ProjectGlobalConfig.update_or_create(
                    defaults={"config_type": ConfigType.scalar, "value": str(value)},
                    project_id=project_id,
                    name=key,
                )

    @classmethod
    def _to_out(cls, config: ProjectGlobalConfig) -> ConfigItemOut:
        return ConfigItemOut(
            id=config.id,
            environment_id=0,
            config_group="envs",
            name=config.name,
            config_type=config.config_type,
            value=cls._mask_for_response(config.config_type, config.value),
            remark=config.remark,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
