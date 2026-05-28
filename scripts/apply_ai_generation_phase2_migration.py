"""手动应用 ai_generation Phase2 迁移（幂等）。"""

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.config import TORTOISE_ORM  # noqa: E402

MIGRATION_FILE = ROOT / "migrations" / "models" / "8_20260529120000_ai_generation_phase2.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("ai_gen_phase2", MIGRATION_FILE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


async def _column_exists(conn, table: str, column: str) -> bool:
    rows = await conn.execute_query_dict(
        """
        SELECT 1 AS ok FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        LIMIT 1
        """,
        [table, column],
    )
    return bool(rows)


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
    migration = _load_migration()
    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection("default")

    need_apply = not await _column_exists(conn, "ai_generation_session", "source_channel")
    need_apply = need_apply or not await _table_exists(conn, "ai_generation_message")

    if need_apply:
        sql = await migration.upgrade(conn)
        await conn.execute_script(sql)
        print("ai_generation phase2 migration applied")
    else:
        print("phase2 schema already present, skip")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
