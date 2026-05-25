import copy
import json

from service.core.enums import ConfigType
from service.core.secret_crypto import decrypt_secret
from service.test_environment.models import (
    DebugRuntimeVar,
    EnvironmentDbRelation,
    EnvironmentFunctionRelation,
    TestEnvironment,
    TestEnvironmentConfig,
    TestEnvironmentSnapshot,
)


def _maybe_decrypt(value: str | None, config_type: ConfigType) -> str | None:
    if value is None:
        return None
    if config_type == ConfigType.secret:
        try:
            return decrypt_secret(value)
        except Exception:
            return value
    return value


def _mask_value(value: str | None) -> str:
    if not value:
        return "***"
    return "***"


def build_payload_summary(payload: dict) -> dict:
    summary = copy.deepcopy(payload)
    if "envs" in summary and isinstance(summary["envs"], dict):
        summary["envs"] = {k: _mask_value(v) if v else v for k, v in summary["envs"].items()}
    if "db" in summary and isinstance(summary["db"], list):
        for item in summary["db"]:
            cfg = item.get("config") or {}
            if "password" in cfg:
                cfg["password"] = _mask_value(cfg.get("password"))
    if "global_func" in summary:
        code = summary.get("global_func") or ""
        summary["global_func"] = f"<{len(code)} chars>" if code else ""
    return summary


class TestEnvDataAssembler:
    @classmethod
    async def assemble(cls, environment_id: int) -> dict:
        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise ValueError(f"environment {environment_id} not found")

        configs = await TestEnvironmentConfig.filter(environment_id=environment_id)
        base_url = ""
        headers: dict[str, str] = {}
        envs: dict[str, str] = {}

        for cfg in configs:
            val = _maybe_decrypt(cfg.value, cfg.config_type)
            if cfg.config_group == "base" and cfg.name == "base_url":
                base_url = val or ""
            elif cfg.config_group == "headers":
                headers[cfg.name] = val or ""
            elif cfg.config_group == "envs":
                if cfg.config_type == ConfigType.json and val:
                    try:
                        parsed = json.loads(val)
                        if isinstance(parsed, dict):
                            envs.update({str(k): str(v) for k, v in parsed.items()})
                            continue
                    except json.JSONDecodeError:
                        pass
                envs[cfg.name] = val or ""

        relations = (
            await EnvironmentDbRelation.filter(environment_id=environment_id)
            .prefetch_related("db_connection")
            .order_by("id")
        )
        db_list = []
        for rel in relations:
            conn = rel.db_connection
            cfg = copy.deepcopy(conn.config or {})
            pwd = cfg.get("password")
            if pwd:
                try:
                    cfg["password"] = decrypt_secret(pwd)
                except Exception:
                    pass
            if "username" in cfg and "user" not in cfg:
                cfg["user"] = cfg["username"]
            db_list.append(
                {
                    "name": conn.server_name,
                    "type": conn.db_type.value if hasattr(conn.db_type, "value") else conn.db_type,
                    "config": cfg,
                }
            )

        func_relations = (
            await EnvironmentFunctionRelation.filter(environment_id=environment_id)
            .prefetch_related("function_file")
            .order_by("sort_order", "id")
        )
        global_func = "\n\n".join(
            rel.function_file.source_code for rel in func_relations if rel.function_file
        )

        return {
            "base_url": base_url,
            "headers": headers,
            "envs": envs,
            "global_func": global_func,
            "db": db_list,
        }

    @classmethod
    async def merge_debug_vars(cls, payload: dict, environment_id: int) -> dict:
        result = copy.deepcopy(payload)
        envs = dict(result.get("envs") or {})
        debug_vars = await DebugRuntimeVar.filter(environment_id=environment_id)
        for var in debug_vars:
            envs[var.var_key] = var.var_value or ""
        result["envs"] = envs
        return result

    @classmethod
    async def get_test_env_data(
        cls,
        environment_id: int,
        *,
        use_snapshot: bool = False,
        merge_debug: bool = False,
    ) -> dict:
        if use_snapshot:
            snapshot = (
                await TestEnvironmentSnapshot.filter(
                    environment_id=environment_id, is_active=True
                )
                .order_by("-created_at")
                .first()
            )
            if snapshot:
                payload = copy.deepcopy(snapshot.payload)
                if merge_debug:
                    return await cls.merge_debug_vars(payload, environment_id)
                return payload
        payload = await cls.assemble(environment_id)
        if merge_debug:
            return await cls.merge_debug_vars(payload, environment_id)
        return payload
