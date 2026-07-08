"""
数据库导出脚本 — 从源库导出全量数据。

用法（在项目根目录执行）：
    python deploy/scripts/export_data.py --output backup.sql       # SQL 格式（推荐，最完整）
    python deploy/scripts/export_data.py --output backup.json      # JSON 格式（跨数据库兼容）
    python deploy/scripts/export_data.py --output backup.sql --no-data  # 仅导出表结构

SQL 格式：调用 mysqldump，保留 schema + data + indexes + FK constraints
JSON 格式：Python 导出，按 FK 依赖顺序排列，适合跨数据库迁移
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def parse_db_url(url: str) -> dict:
    """从 DATABASE_URL 解析 MySQL 连接参数"""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username or "",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/"),
    }


# FK 依赖层级（Tier 0 无依赖，先导出；Tier 10 叶子表，最后导出）
EXPORT_ORDER = [
    # Tier 0
    "user",
    # Tier 1
    "project",
    # Tier 2
    "project_member", "project_module", "db_connection",
    "env_catalog", "env_function_file", "env_uploaded_file", "project_global_config",
    # Tier 3
    "db_connection_test_log", "test_environment", "knowledge_workspace",
    "functional_case_catalog", "api_interface_catalog",
    # Tier 4
    "test_environment_config", "environment_db_relation",
    "environment_function_relation", "test_environment_snapshot", "knowledge_document",
    # Tier 5
    "knowledge_document_version", "ai_generation_session", "api_interface",
    # Tier 6
    "api_interface_debug_template", "api_dependency_group",
    "functional_test_point", "functional_case", "api_base_case",
    # Tier 7
    "api_dependency", "api_test_case", "test_suite", "test_task", "test_defect",
    # Tier 8
    "suite_case_relation", "task_suite_relation", "task_case_relation",
    "test_defect_comment", "test_defect_history", "test_task_run",
    # Tier 9
    "test_suite_run", "functional_case_run_record",
    # Tier 10
    "api_case_run_record", "ai_generation_message",
]


def export_sql(output: str, no_data: bool = False):
    """使用 mysqldump 导出 SQL"""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("[FAIL] DATABASE_URL 未配置")
        sys.exit(1)

    db = parse_db_url(db_url)
    cmd = [
        "mysqldump",
        "-h", db["host"], "-P", str(db["port"]),
        "-u", db["user"], f"-p{db['password']}",
        "--single-transaction",
        "--routines", "--triggers",
        "--set-gtid-purged=OFF",
    ]
    if no_data:
        cmd.append("--no-data")
    cmd.append(db["database"])

    print(f">>> mysqldump → {output}")
    with open(output, "w", encoding="utf-8") as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"[FAIL] mysqldump 失败: {result.stderr}")
        sys.exit(1)

    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"[OK] 导出完成: {output} ({size_mb:.1f} MB)")


async def export_json(output: str):
    """使用 Tortoise ORM 导出 JSON（按 FK 顺序）"""
    from tortoise import Tortoise
    from service.core.settings import TORTOISE_ORM

    await Tortoise.init(config=TORTOISE_ORM)

    data = {}
    for table_name in EXPORT_ORDER:
        try:
            conn = Tortoise.get_connection("default")
            _, rows = await conn.execute_query(f"SELECT * FROM `{table_name}`")
            # 序列化日期类型
            for row in rows:
                for k, v in row.items():
                    if isinstance(v, (datetime, date)):
                        row[k] = v.isoformat()
                    elif isinstance(v, bytes):
                        row[k] = v.hex()
            data[table_name] = rows
            print(f"  {table_name}: {len(rows)} 条记录")
        except Exception as e:
            print(f"  [WARN]  {table_name}: {e}")
            data[table_name] = []

    await Tortoise.close_connections()

    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_mb = os.path.getsize(output) / 1024 / 1024
    print(f"[OK] 导出完成: {output} ({size_mb:.1f} MB)")


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "--output":
        print(__doc__)
        sys.exit(1)

    output = sys.argv[2]
    no_data = "--no-data" in sys.argv

    if output.endswith(".sql"):
        export_sql(output, no_data)
    elif output.endswith(".json"):
        asyncio.run(export_json(output))
    else:
        print("[FAIL] 输出文件格式必须为 .sql 或 .json")
        sys.exit(1)


if __name__ == "__main__":
    main()
