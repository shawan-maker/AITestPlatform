"""修复/续跑 functional FT-A 迁移（幂等）。"""

import asyncio
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.config import TORTOISE_ORM  # noqa: E402


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


async def main() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection("default")

    if not await _table_exists(conn, "requirement_candidate"):
        spec = importlib.util.spec_from_file_location(
            "functional_migration_ft_a",
            ROOT / "scripts" / "migrations" / "models" / "4_20260526100000_functional_module_ft_a.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        await conn.execute_script(await module.upgrade(conn))
        print("functional FT-A migration applied")
    else:
        print("requirement_candidate already exists, skip create tables")

    if not await _column_exists(conn, "requirement_doc", "source_type"):
        await conn.execute_script(
            """
            ALTER TABLE `requirement_doc`
                ADD COLUMN `source_type` VARCHAR(9) NOT NULL DEFAULT 'manual' AFTER `status`;
            UPDATE `requirement_doc` SET `source_type` = 'knowledge'
            WHERE `source_document_id` IS NOT NULL;
            """
        )
        print("added requirement_doc.source_type")

    if not await _column_exists(conn, "functional_case", "exec_result"):
        await conn.execute_script(
            """
            ALTER TABLE `functional_case`
                ADD COLUMN `exec_result` VARCHAR(7) NOT NULL DEFAULT 'pending' AFTER `status`,
                ADD COLUMN `jira_issue_key` VARCHAR(50) NULL AFTER `actual_result`,
                ADD COLUMN `sort_order` INT NOT NULL DEFAULT 0 AFTER `jira_issue_key`,
                ADD COLUMN `catalog_id` INT NULL AFTER `module_id`,
                ADD COLUMN `updated_by_id` INT NULL AFTER `created_by_id`;
            """
        )
        print("added functional_case columns")

    if not await _column_exists(conn, "ai_generation_session", "output_payload"):
        await conn.execute_script(
            """
            ALTER TABLE `ai_generation_session`
                ADD COLUMN `output_payload` JSON NULL AFTER `error_message`,
                ADD COLUMN `user_prompt` LONGTEXT NULL AFTER `output_payload`;
            """
        )
        print("added ai_generation_session columns")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
