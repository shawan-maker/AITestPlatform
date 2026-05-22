from tortoise import Tortoise

from service.core.config import TORTOISE_ORM


async def init_db() -> None:
    await Tortoise.init(config=TORTOISE_ORM)


async def close_db() -> None:
    await Tortoise.close_connections()


async def generate_schemas() -> None:
    """仅用于本地快速建表；生产环境请使用 Aerich：python scripts/db_manage.py upgrade"""
    await Tortoise.generate_schemas()
