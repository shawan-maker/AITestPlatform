from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `test_defect`
            ADD COLUMN `defect_category` VARCHAR(14) NOT NULL DEFAULT 'other'
                COMMENT 'functional: functional\\nperformance: performance\\nui: ui\\ncompatibility: compatibility\\nsecurity: security\\nother: other' AFTER `status`,
            ADD COLUMN `root_cause` LONGTEXT NULL AFTER `defect_category`,
            ADD COLUMN `assignee_id` INT NULL AFTER `created_by_id`,
            ADD COLUMN `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) AFTER `created_at`,
            ADD COLUMN `updated_by_id` INT NULL AFTER `updated_at`,
            MODIFY COLUMN `status` VARCHAR(12) NOT NULL DEFAULT 'init'
                COMMENT 'init: init\\nopen: open\\nin_progress: in_progress\\nresolved: resolved\\nclosed: closed',
            MODIFY COLUMN `source_type` VARCHAR(16) NOT NULL
                COMMENT 'api_case: api_case\\nfunctional_case: functional_case\\nmanual: manual',
            ADD CONSTRAINT `fk_test_defect_assignee` FOREIGN KEY (`assignee_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_test_defect_updated_by` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
            ADD INDEX `idx_test_defect_proj_status` (`project_id`, `status`),
            ADD INDEX `idx_test_defect_proj_created` (`project_id`, `created_at`),
            ADD INDEX `idx_test_defect_assignee` (`assignee_id`);

        CREATE TABLE IF NOT EXISTS `test_defect_comment` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `content` LONGTEXT NOT NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `created_by_id` INT NULL,
            `defect_id` INT NOT NULL,
            CONSTRAINT `fk_test_defect_comment_defect` FOREIGN KEY (`defect_id`) REFERENCES `test_defect` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_test_defect_comment_created_by` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
            KEY `idx_test_defect_comment_defect` (`defect_id`, `created_at`)
        ) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `test_defect_history` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `action` VARCHAR(14) NOT NULL
                COMMENT 'status_change: status_change\\nfield_update: field_update\\ncomment_added: comment_added\\ncreated: created',
            `field_name` VARCHAR(64) NULL,
            `old_value` LONGTEXT NULL,
            `new_value` LONGTEXT NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `defect_id` INT NOT NULL,
            `operator_id` INT NULL,
            CONSTRAINT `fk_test_defect_history_defect` FOREIGN KEY (`defect_id`) REFERENCES `test_defect` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_test_defect_history_operator` FOREIGN KEY (`operator_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
            KEY `idx_test_defect_history_defect` (`defect_id`, `created_at`)
        ) CHARACTER SET utf8mb4;
    """
