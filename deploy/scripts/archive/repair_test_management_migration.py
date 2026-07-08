"""修复/续跑 test_management v1 迁移（幂等）。"""

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

    if not await _table_exists(conn, "task_case_relation"):
        spec = importlib.util.spec_from_file_location(
            "test_management_migration_v1",
            ROOT / "scripts" / "migrations" / "models" / "6_20260527120000_test_management_v1.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        await conn.execute_script(await module.upgrade(conn))
        print("test_management v1 migration applied")
    else:
        print("task_case_relation already exists, skip")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
