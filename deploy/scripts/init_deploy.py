"""
全新部署初始化脚本。

用法（在项目根目录执行）：
    python deploy/scripts/init_deploy.py              # 正式执行
    python deploy/scripts/init_deploy.py --dry-run     # 仅检查，不执行

流程：
    1. 检查 .env 配置
    2. 检查数据库连接（使用 asyncmy，兼容 Docker 容器内 MySQL 8.0）
    3. 创建数据库（如不存在）
    4. 运行 Aerich init-db（首次建表）
    5. 运行 Aerich upgrade（应用所有迁移）
    6. 验证：查询各表记录数

注意：
    Docker 容器内的 MySQL 8.0 默认启用 TLS，mysql CLI 客户端会因证书验证失败。
    本脚本使用 asyncmy Python 驱动连接数据库，不受此问题影响。
    如 aerich upgrade 超时（国内网络偶发），自动回退到 Tortoise.generate_schemas()。
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def parse_db_url(url: str) -> dict:
    """从 DATABASE_URL 解析 MySQL 连接参数"""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/"),
    }


async def async_mysql_connect(db: dict):
    """使用 asyncmy 连接 MySQL（兼容 Docker 容器内 MySQL 8.0 TLS）"""
    import asyncmy

    conn = await asyncmy.connect(
        host=db["host"],
        port=db["port"],
        user=db["user"],
        password=db["password"],
    )
    return conn


async def async_mysql_query(db: dict, sql: str, database: str | None = None):
    """执行 SQL 查询并返回结果"""
    import asyncmy

    conn = await asyncmy.connect(
        host=db["host"],
        port=db["port"],
        user=db["user"],
        password=db["password"],
        db=database,
    )
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(sql)
            rows = await cursor.fetchall()
            desc = cursor.description
            columns = [col[0] for col in desc] if desc else []
            return columns, rows
    finally:
        conn.close()


async def async_mysql_execute(db: dict, sql: str):
    """执行 SQL（无返回）"""
    import asyncmy

    conn = await asyncmy.connect(
        host=db["host"],
        port=db["port"],
        user=db["user"],
        password=db["password"],
    )
    try:
        async with conn.cursor() as cursor:
            await cursor.execute(sql)
        await conn.commit()
    finally:
        conn.close()


def run_cmd(cmd: list[str], check: bool = True, timeout: int = 60, **kwargs) -> subprocess.CompletedProcess:
    """执行命令并打印结果"""
    print(f"  >>> {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=timeout, **kwargs)
    if result.stdout.strip():
        print(f"  {result.stdout.strip()}")
    if result.returncode != 0 and result.stderr.strip():
        print(f"  [stderr] {result.stderr.strip()}")
    if check and result.returncode != 0:
        print(f"  [FAIL] 命令失败 (exit code {result.returncode})")
        sys.exit(1)
    return result


def main():
    dry_run = "--dry-run" in sys.argv
    print("=" * 60)
    print("AITestPlatform 部署初始化")
    print("=" * 60)

    # --- Step 1: 检查 .env ---
    print("\n[1/6] 检查 .env 配置...")
    env_file = ROOT / ".env"
    if not env_file.exists():
        print("  [FAIL] .env 文件不存在，请从 .env.example 复制并填写配置")
        sys.exit(1)

    # 读取关键配置
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    db_url = os.getenv("DATABASE_URL", "")
    jwt_key = os.getenv("JWT_SECRET_KEY", "")

    if not db_url:
        print("  [FAIL] DATABASE_URL 未配置")
        sys.exit(1)
    if jwt_key in ("", "change-me-in-production", "please-generate-a-random-secret-key"):
        print("  [WARN]  JWT_SECRET_KEY 使用了默认值，请在 .env 中设置安全密钥")

    db = parse_db_url(db_url)
    print(f"  数据库: {db['host']}:{db['port']}/{db['database']}")
    print(f"  用户: {db['user']}")
    print("  [OK] .env 配置检查通过")

    if dry_run:
        print("\n[dry-run] 后续步骤：")
        print("  [2] 检查数据库连接")
        print("  [3] 创建数据库（如不存在）")
        print("  [4] Aerich init-db")
        print("  [5] Aerich upgrade")
        print("  [6] 验证表结构")
        return

    # --- Step 2: 检查数据库连接（使用 asyncmy，避免 mysql CLI SSL 证书问题）---
    print("\n[2/6] 检查数据库连接...")
    try:
        asyncio.run(async_mysql_execute(db, "SELECT 1"))
        print("  [OK] MySQL 连接成功")
    except Exception as e:
        print(f"  [FAIL] 无法连接 MySQL: {e}")
        sys.exit(1)

    # --- Step 3: 创建数据库（如不存在）---
    print("\n[3/6] 创建数据库（如不存在）...")
    try:
        create_sql = f"CREATE DATABASE IF NOT EXISTS `{db['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        asyncio.run(async_mysql_execute(db, create_sql))
        print(f"  [OK] 数据库 {db['database']} 就绪")
    except Exception as e:
        print(f"  [FAIL] 创建数据库失败: {e}")
        sys.exit(1)

    # --- Step 4: Aerich init-db ---
    print("\n[4/6] Aerich init-db...")
    try:
        run_cmd(["aerich", "init-db"], check=False, timeout=30)
    except subprocess.TimeoutExpired:
        print("  [WARN]  aerich init-db 超时，继续下一步...")
    except Exception as e:
        print(f"  [WARN]  init-db 可能已执行过: {e}")

    # --- Step 5: Aerich upgrade ---
    print("\n[5/6] Aerich upgrade...")
    try:
        run_cmd(["aerich", "upgrade"], timeout=60)
        print("  [OK] 数据库迁移已应用")
    except subprocess.TimeoutExpired:
        print("  [WARN]  aerich upgrade 超时，回退到 Tortoise.generate_schemas()...")
        _fallback_generate_schemas(db_url)
    except Exception as e:
        print(f"  [WARN]  aerich upgrade 失败: {e}")
        print("  回退到 Tortoise.generate_schemas()...")
        _fallback_generate_schemas(db_url)

    # --- Step 6: 验证 ---
    print("\n[6/6] 验证表结构...")
    try:
        columns, rows = asyncio.run(
            async_mysql_query(db, "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES "
                              f"WHERE TABLE_SCHEMA='{db['database']}' ORDER BY TABLE_NAME",
                              database=db["database"])
        )
        if rows:
            print(f"  {'表名':<40} {'行数':>10}")
            print(f"  {'-'*40} {'-'*10}")
            for row in rows:
                print(f"  {row[0]:<40} {row[1]:>10}")
        else:
            print("  [WARN] 未发现任何表")
    except Exception as e:
        print(f"  [WARN] 验证失败: {e}")

    print("\n" + "=" * 60)
    print("[OK] 部署初始化完成！")
    print()
    print("后续步骤：")
    print("  1. 重启后端: docker compose -f deploy/multi-container/docker-compose.yml restart backend")
    print("     (或本地: python main.py)")
    print("  2. 后端会自动创建默认管理员 (admin / 123456)")
    print("  3. 如从旧实例迁移数据: python deploy/scripts/import_data.py --input backup.sql")
    print("  4. 构建前端: cd frontend && npm run build")
    print("=" * 60)


def _fallback_generate_schemas(db_url: str):
    """当 aerich upgrade 超时时，使用 Tortoise ORM 直接建表作为回退方案。

    这在 Docker 容器内部尤其有用，因为 aerich 可能因网络或驱动问题超时。
    """
    import asyncio
    from tortoise import Tortoise

    async def _run():
        # 加载项目配置（需要在 sys.path 中有项目根目录）
        sys.path.insert(0, str(ROOT))
        from service.core.settings import TORTOISE_ORM

        await Tortoise.init(config=TORTOISE_ORM, _enable_global_fallback=True)
        await Tortoise.generate_schemas(safe=True)

        # 验证
        conn = Tortoise.get_connection("default")
        _, rows = await conn.execute_query("SHOW TABLES")
        table_count = len(rows)
        print(f"  [OK] Tortoise.generate_schemas 完成，共创建 {table_count} 张表")

        await Tortoise.close_connections()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
