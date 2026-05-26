"""修复/续跑 api_test v1 迁移（幂等）。"""

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.config import TORTOISE_ORM  # noqa: E402


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


async def main() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection("default")

    if not await _table_exists(conn, "api_interface_catalog"):
        spec = importlib.util.spec_from_file_location(
            "api_test_migration_v1",
            ROOT / "migrations" / "models" / "5_20260526120000_api_test_module_v1.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        await conn.execute_script(await module.upgrade(conn))
        print("api_test v1 migration applied")
    else:
        print("api_interface_catalog already exists, skip")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
