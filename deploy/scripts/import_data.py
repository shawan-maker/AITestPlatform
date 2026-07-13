"""
数据库导入脚本 — 将数据导入到目标库。

用法（在项目根目录执行）：
    python deploy/scripts/import_data.py --input backup.sql          # SQL 格式导入
    python deploy/scripts/import_data.py --input backup.json         # JSON 格式导入
    python deploy/scripts/import_data.py --input backup.json --on-conflict=skip  # 跳过重复记录

SQL 格式：调用 mysql 客户端直接导入（最快速）
JSON 格式：Python 按 FK 顺序逐表导入，支持冲突处理

冲突处理策略（--on-conflict）：
    skip   - 跳过已存在的记录（默认）
    update - 更新已存在的记录
    error  - 遇到冲突立即报错
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


# FK 依赖层级（必须按此顺序导入）
IMPORT_ORDER = [
    "user",
    "project",
    "project_member", "project_module", "db_connection",
    "env_catalog", "env_function_file", "env_uploaded_file", "project_global_config",
    "db_connection_test_log", "test_environment", "knowledge_workspace",
    "functional_case_catalog", "api_interface_catalog",
    "test_environment_config", "environment_db_relation",
    "environment_function_relation", "test_environment_snapshot", "knowledge_document",
    "knowledge_document_version", "ai_generation_session", "api_interface",
    "api_interface_debug_template", "api_dependency_group",
    "functional_test_point", "functional_case", "api_base_case",
    "api_dependency", "api_test_case", "test_suite", "test_task", "test_defect",
    "suite_case_relation", "task_suite_relation", "task_case_relation",
    "test_defect_comment", "test_defect_history", "test_task_run",
    "test_suite_run", "functional_case_run_record",
    "api_case_run_record", "ai_generation_message",
]


def import_sql(input_file: str):
    """使用 mysql 客户端导入 SQL"""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("[FAIL] DATABASE_URL 未配置")
        sys.exit(1)

    db = parse_db_url(db_url)
    cmd = [
        "mysql",
        "-h", db["host"], "-P", str(db["port"]),
        "-u", db["user"], f"-p{db['password']}",
        db["database"],
    ]

    size_mb = os.path.getsize(input_file) / 1024 / 1024
    print(f">>> mysql ← {input_file} ({size_mb:.1f} MB)")

    with open(input_file, "r", encoding="utf-8") as f:
        result = subprocess.run(cmd, stdin=f, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[FAIL] 导入失败: {result.stderr}")
        sys.exit(1)

    print("[OK] SQL 导入完成")


async def import_json(input_file: str, on_conflict: str = "skip"):
    """使用 Tortoise ORM 导入 JSON"""
    from tortoise import Tortoise
    from service.core.settings import TORTOISE_ORM

    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection("default")

    # 禁用外键检查以允许任意导入顺序
    await conn.execute_script("SET FOREIGN_KEY_CHECKS=0;\n")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_imported = 0
    total_skipped = 0

    for table_name in IMPORT_ORDER:
        rows = data.get(table_name, [])
        if not rows:
            continue

        imported = 0
        skipped = 0
        errors = 0

        for row in rows:
            # 反序列化日期字段
            for k, v in row.items():
                if isinstance(v, str) and len(v) >= 10:
                    try:
                        if "T" in v:
                            row[k] = datetime.fromisoformat(v)
                        else:
                            row[k] = date.fromisoformat(v)
                    except (ValueError, TypeError):
                        pass

            cols = ", ".join(f"`{k}`" for k in row.keys())
            # Tortoise ORM MySQL 后端使用 %s 作为占位符
            placeholders = ", ".join("%s" for _ in row)
            values = list(row.values())

            if on_conflict == "skip":
                # INSERT IGNORE
                sql = f"INSERT IGNORE INTO `{table_name}` ({cols}) VALUES ({placeholders})"
            elif on_conflict == "update":
                # REPLACE INTO
                sql = f"REPLACE INTO `{table_name}` ({cols}) VALUES ({placeholders})"
            else:
                # 普通 INSERT
                sql = f"INSERT INTO `{table_name}` ({cols}) VALUES ({placeholders})"

            try:
                await conn.execute_query(sql, values)
                imported += 1
            except Exception as e:
                if on_conflict == "error":
                    print(f"  [FAIL] {table_name}: {e}")
                    await conn.execute_script("SET FOREIGN_KEY_CHECKS=1;\n")
                    await Tortoise.close_connections()
                    sys.exit(1)
                elif on_conflict == "skip":
                    skipped += 1
                else:
                    errors += 1
                    if errors <= 3:
                        print(f"  [WARN]  {table_name}: {e}")

        total_imported += imported
        total_skipped += skipped
        if imported or skipped:
            print(f"  {table_name}: {imported} imported, {skipped} skipped")

    # 恢复外键检查
    await conn.execute_script("SET FOREIGN_KEY_CHECKS=1;\n")
    await Tortoise.close_connections()

    print(f"\n[OK] 导入完成: {total_imported} 条导入, {total_skipped} 条跳过")


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "--input":
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[2]
    if not os.path.exists(input_file):
        print(f"[FAIL] 文件不存在: {input_file}")
        sys.exit(1)

    on_conflict = "skip"
    for arg in sys.argv:
        if arg.startswith("--on-conflict="):
            on_conflict = arg.split("=", 1)[1]

    if input_file.endswith(".sql"):
        import_sql(input_file)
    elif input_file.endswith(".json"):
        asyncio.run(import_json(input_file, on_conflict))
    else:
        print("[FAIL] 输入文件格式必须为 .sql 或 .json")
        sys.exit(1)


if __name__ == "__main__":
    main()
