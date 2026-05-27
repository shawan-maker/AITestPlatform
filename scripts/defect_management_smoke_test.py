"""缺陷管理模块冒烟测试（需本地 DB 与迁移）。"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.config import TORTOISE_ORM  # noqa: E402
from service.core.enums import DefectCategory, DefectStatus  # noqa: E402
from service.test_execution.models import TestDefect  # noqa: E402
from service.test_management.defect.transition import ALLOWED_TRANSITIONS  # noqa: E402


async def main() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        count = await TestDefect.all().count()
        print(f"test_defect rows: {count}")
        print("enums OK:", DefectCategory.functional, DefectStatus.init)
        print("transitions OK:", len(ALLOWED_TRANSITIONS))
        print("defect_management smoke: PASS")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
