from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `requirement_candidate` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `description` LONGTEXT,
    `source_document_version_id` INT NOT NULL,
    `source_version_label` VARCHAR(20) NOT NULL,
    `index_status` VARCHAR(8) NOT NULL DEFAULT 'indexed',
    `indexed_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT NOT NULL,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `source_document_id` INT NOT NULL,
    UNIQUE KEY `uid_req_cand_src_ver` (`source_document_id`, `source_document_version_id`),
    CONSTRAINT `fk_req_cand_user` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_req_cand_module` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_req_cand_project` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_req_cand_doc` FOREIGN KEY (`source_document_id`) REFERENCES `knowledge_document` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `functional_case_catalog` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `level` SMALLINT NOT NULL DEFAULT 1,
    `sort_order` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `parent_id` INT,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_func_cat_proj_parent_name` (`project_id`, `parent_id`, `name`),
    CONSTRAINT `fk_func_cat_parent` FOREIGN KEY (`parent_id`) REFERENCES `functional_case_catalog` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_func_cat_project` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

        ALTER TABLE `requirement_doc`
            ADD COLUMN `source_type` VARCHAR(9) NOT NULL DEFAULT 'manual'
                COMMENT 'knowledge: knowledge\\nmanual: manual' AFTER `status`;

        UPDATE `requirement_doc`
        SET `source_type` = 'knowledge'
        WHERE `source_document_id` IS NOT NULL;

        UPDATE `requirement_doc` rd
        INNER JOIN (
            SELECT `project_id`, `title`, MIN(`id`) AS keep_id, COUNT(*) AS cnt
            FROM `requirement_doc`
            GROUP BY `project_id`, `title`
            HAVING cnt > 1
        ) dup ON dup.project_id = rd.project_id AND dup.title = rd.title AND rd.id <> dup.keep_id
        SET rd.title = CONCAT(rd.title, ' (dup-', rd.id, ')');

        ALTER TABLE `requirement_doc`
            ADD UNIQUE KEY `uid_requirement_project_title` (`project_id`, `title`);

        ALTER TABLE `functional_case`
            ADD COLUMN `exec_result` VARCHAR(7) NOT NULL DEFAULT 'pending'
                COMMENT 'pending: pending\\npassed: passed\\nfailed: failed\\nblocked: blocked\\nskipped: skipped' AFTER `status`,
            ADD COLUMN `jira_issue_key` VARCHAR(50) NULL AFTER `actual_result`,
            ADD COLUMN `sort_order` INT NOT NULL DEFAULT 0 AFTER `jira_issue_key`,
            ADD COLUMN `catalog_id` INT NULL AFTER `module_id`,
            ADD COLUMN `updated_by_id` INT NULL AFTER `created_by_id`,
            ADD CONSTRAINT `fk_func_case_catalog` FOREIGN KEY (`catalog_id`) REFERENCES `functional_case_catalog` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_func_case_updated_by` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL;

        ALTER TABLE `ai_generation_session`
            ADD COLUMN `output_payload` JSON NULL AFTER `error_message`,
            ADD COLUMN `user_prompt` LONGTEXT NULL AFTER `output_payload`;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ai_generation_session`
            DROP COLUMN `user_prompt`,
            DROP COLUMN `output_payload`;

        ALTER TABLE `functional_case`
            DROP FOREIGN KEY `fk_func_case_updated_by`,
            DROP FOREIGN KEY `fk_func_case_catalog`,
            DROP COLUMN `updated_by_id`,
            DROP COLUMN `catalog_id`,
            DROP COLUMN `sort_order`,
            DROP COLUMN `jira_issue_key`,
            DROP COLUMN `exec_result`;

        ALTER TABLE `requirement_doc`
            DROP INDEX `uid_requirement_project_title`,
            DROP COLUMN `source_type`;

        DROP TABLE IF EXISTS `functional_case_catalog`;
        DROP TABLE IF EXISTS `requirement_candidate`;
        """
