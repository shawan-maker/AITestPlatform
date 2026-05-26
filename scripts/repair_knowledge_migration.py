"""修复/续跑 knowledge Phase A 迁移（幂等）。"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tortoise import Tortoise  # noqa: E402

from service.core.config import TORTOISE_ORM  # noqa: E402


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
    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection("default")

    if not await _table_exists(conn, "knowledge_document_version"):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "knowledge_migration_v1",
            ROOT / "migrations" / "models" / "3_20260525200000_knowledge_module_v1.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        await conn.execute_script(await module.upgrade(conn))
        print("full migration applied")
        await Tortoise.close_connections()
        return

    if await _column_exists(conn, "knowledge_document", "file_name"):
        if not await _column_exists(conn, "knowledge_document", "parse_mode"):
            await conn.execute_script(
                """
                ALTER TABLE `knowledge_document`
                    ADD COLUMN `parse_mode` VARCHAR(8) NOT NULL DEFAULT 'ai' AFTER `doc_type`,
                    ADD COLUMN `current_version_id` INT NULL AFTER `title`;
                """
            )
        count = await conn.execute_query_dict(
            "SELECT COUNT(*) AS c FROM knowledge_document_version"
        )
        if count[0]["c"] == 0:
            await conn.execute_script(
                """
                INSERT INTO `knowledge_document_version` (
                    `document_id`, `version_label`, `version_seq`, `file_name`, `file_path`,
                    `file_hash`, `mime_type`, `file_size`, `file_expired`, `index_status`,
                    `index_error`, `indexed_at`, `created_by_id`, `created_at`
                )
                SELECT
                    `id`,
                    CONCAT('v1.', GREATEST(`version` - 1, 0)),
                    `version`,
                    `file_name`, `file_path`, `file_hash`, `mime_type`, `file_size`,
                    0, `index_status`, `index_error`, `indexed_at`, `created_by_id`, `created_at`
                FROM `knowledge_document`;
                """
            )
        await conn.execute_script(
            """
            UPDATE `knowledge_document` d
            INNER JOIN `knowledge_document_version` v
                ON v.document_id = d.id AND v.version_seq = d.version
            SET d.current_version_id = v.id
            WHERE d.current_version_id IS NULL;
            """
        )
        await conn.execute_script(
            """
            ALTER TABLE `knowledge_document`
                DROP INDEX `idx_knowledge_d_project_c4195a`,
                ADD KEY `idx_knowledg_workspace_fk` (`workspace_id`),
                DROP INDEX `idx_knowledge_d_workspa_874e8b`,
                DROP FOREIGN KEY `fk_knowledg_user_562bedd9`,
                DROP COLUMN `file_name`,
                DROP COLUMN `file_path`,
                DROP COLUMN `file_hash`,
                DROP COLUMN `mime_type`,
                DROP COLUMN `file_size`,
                DROP COLUMN `version`,
                DROP COLUMN `index_status`,
                DROP COLUMN `index_error`,
                DROP COLUMN `indexed_at`,
                DROP COLUMN `linked_requirement_id`,
                DROP COLUMN `created_by_id`,
                ADD UNIQUE KEY `uid_knowledg_project_title` (`project_id`, `title`),
                ADD KEY `idx_knowledg_doc_proj_type_upd` (`project_id`, `doc_type`, `updated_at`);
            """
        )
        print("knowledge_document alter completed")

    if not await _column_exists(conn, "requirement_doc", "source_document_version_id"):
        await conn.execute_script(
            """
            ALTER TABLE `requirement_doc`
                ADD COLUMN `source_document_version_id` INT NULL AFTER `source_document_id`,
                ADD COLUMN `source_version_label` VARCHAR(20) NULL AFTER `source_document_version_id`;
            """
        )
        print("requirement_doc columns added")

    print("repair done")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
