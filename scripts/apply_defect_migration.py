"""手动应用 defect_management_v1 迁移（当 aerich upgrade 失败时使用）。"""

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.config import TORTOISE_ORM  # noqa: E402

MIGRATION_FILE = ROOT / "scripts" / "migrations" / "models" / "7_20260528120000_defect_management_v1.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("defect_migration_v1", MIGRATION_FILE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


async def main() -> None:
    migration = _load_migration()
    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection("default")
    check = await conn.execute_query("SHOW COLUMNS FROM `test_defect` LIKE 'assignee_id'")
    if check[1]:
        print("assignee_id already exists, skip")
    else:
        sql = await migration.upgrade(conn)
        await conn.execute_script(sql)
        print("defect migration 7 applied")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
