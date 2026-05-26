"""测试管理模块冒烟测试（需本地 DB 与迁移）。"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.config import TORTOISE_ORM  # noqa: E402
from service.core.enums import RunMode, TaskSuiteType  # noqa: E402
from service.test_management.models import TestSuite, TestTask  # noqa: E402


async def main() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        suite_count = await TestSuite.all().count()
        task_count = await TestTask.all().count()
        print(f"test_suite rows: {suite_count}")
        print(f"test_task rows: {task_count}")
        print("ORM enums OK:", TaskSuiteType.api, RunMode.serial)
        print("test_management smoke: PASS")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
