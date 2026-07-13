from tortoise import Tortoise

from service.core.settings import TORTOISE_ORM


async def init_db() -> None:
    # Tortoise ORM 1.1.7+ 使用 contextvars 管理状态，FastAPI lifespan 和
    # HTTP 请求运行在不同 async task 中，需要开启 global fallback 才能跨 task 访问
    await Tortoise.init(config=TORTOISE_ORM, _enable_global_fallback=True)


async def close_db() -> None:
    await Tortoise.close_connections()


async def generate_schemas() -> None:
    """仅用于本地快速建表；生产环境请使用 Aerich：python deploy/scripts/db_manage.py upgrade"""
    await Tortoise.generate_schemas()


async def auto_migrate() -> None:
    """应用所有未执行的 Aerich 迁移（启动时自动调用）。
    
    直接读取迁移文件并执行 SQL，兼容各版本 Aerich 格式，
    不依赖 aerich Command API（避免版本不兼容问题）。
    """
    import importlib.util
    import logging
    from pathlib import Path

    logger = logging.getLogger("auto_migrate")
    migration_dir = Path(__file__).resolve().parents[2] / "scripts" / "migrations" / "models"

    if not migration_dir.is_dir():
        return

    # 收集所有迁移文件并按文件名排序
    files = sorted(
        (f for f in migration_dir.glob("*.py") if f.name != "__init__.py"),
        key=lambda f: f.name,
    )
    if not files:
        return

    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection("default")

    # 获取已应用的迁移版本
    try:
        applied_rows = await conn.execute_query("SELECT version FROM aerich ORDER BY id")
        applied_versions = {row[0] for row in applied_rows[1]}
    except Exception:
        applied_versions = set()

    for f in files:
        version_name = f.stem  # e.g. "11_20260605090000_requirement_doc_updated_by"
        if version_name in applied_versions:
            continue

        try:
            spec = importlib.util.spec_from_file_location(version_name, str(f))
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            
            sql = mod.upgrade(conn.__class__)
            await conn.execute_script(sql)

            # 注册到 aerich 表
            await conn.execute_query(
                "INSERT INTO aerich (version, app, content) VALUES (%s, %s, %s)",
                [version_name, "models", "{}"],
            )
            logger.info("已应用迁移: %s", version_name)
        except Exception as exc:
            logger.error("迁移 %s 执行失败，跳过 | %s", version_name, exc)
