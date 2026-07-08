"""修复/续跑 defect_management v1 迁移（幂等）。"""

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.settings import TORTOISE_ORM  # noqa: E402


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

    if not await _table_exists(conn, "test_defect_comment"):
        spec = importlib.util.spec_from_file_location(
            "defect_management_migration_v1",
            ROOT / "scripts" / "migrations" / "models" / "7_20260528120000_defect_management_v1.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        await conn.execute_script(await module.upgrade(conn))
        print("defect_management v1 migration applied")
    else:
        print("test_defect_comment already exists, skip")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
