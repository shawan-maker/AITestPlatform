"""修复/续跑 env SIT global_config 迁移（幂等），并注册 aerich 版本记录。"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.settings import TORTOISE_ORM  # noqa: E402

MIGRATION_VERSION = "models_9_20260530120000_env_sit_global_config"
MIGRATION_FILE = ROOT / "scripts" / "migrations" / "models" / "9_20260530120000_env_sit_global_config.py"


async def _table_exists(conn, table: str) -> bool:
    rows = await conn.execute_query_dict(
        """
        SELECT 1 AS ok FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        LIMIT 1
        """,
        [table],
    )
    return bool(rows)


async def _aerich_registered(conn, version: str) -> bool:
    rows = await conn.execute_query_dict(
        "SELECT 1 AS ok FROM aerich WHERE app = %s AND version = %s LIMIT 1",
        ["models", version],
    )
    return bool(rows)


async def main() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection("default")

    if not await _table_exists(conn, "project_global_config"):
        spec = importlib.util.spec_from_file_location(
            "env_sit_global_config_migration",
            MIGRATION_FILE,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        await conn.execute_script(await module.upgrade(conn))
        print("env SIT migration applied")
    else:
        print("project_global_config already exists, skip apply")

    if not await _aerich_registered(conn, MIGRATION_VERSION):
        await conn.execute_query(
            "INSERT INTO aerich (version, app, content) VALUES (%s, %s, %s)",
            [MIGRATION_VERSION, "models", json.dumps({})],
        )
        print(f"aerich record registered: {MIGRATION_VERSION}")
    else:
        print("aerich record already present")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
