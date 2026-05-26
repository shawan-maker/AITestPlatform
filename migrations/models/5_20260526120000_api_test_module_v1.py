from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `api_interface_catalog` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `level` SMALLINT NOT NULL DEFAULT 1,
    `sort_order` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `parent_id` INT,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_api_if_cat_proj_parent_name` (`project_id`, `parent_id`, `name`),
    CONSTRAINT `fk_api_if_cat_parent` FOREIGN KEY (`parent_id`) REFERENCES `api_interface_catalog` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_if_cat_project` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

        INSERT INTO `api_interface_catalog` (`name`, `level`, `sort_order`, `project_id`, `parent_id`)
        SELECT '默认', 1, 0, p.id, NULL
        FROM `project` p
        WHERE NOT EXISTS (
            SELECT 1 FROM `api_interface_catalog` c
            WHERE c.project_id = p.id AND c.parent_id IS NULL AND c.name = '默认'
        );

        ALTER TABLE `api_interface`
            ADD COLUMN `is_current` BOOL NOT NULL DEFAULT 1 AFTER `version`,
            ADD COLUMN `sort_order` INT NOT NULL DEFAULT 0 AFTER `is_current`,
            ADD COLUMN `catalog_id` INT NULL AFTER `module_id`,
            ADD COLUMN `source_document_version_id` INT NULL AFTER `source_document_id`,
            ADD COLUMN `created_by_id` INT NULL AFTER `source_document_version_id`,
            ADD COLUMN `updated_by_id` INT NULL AFTER `created_by_id`,
            ADD COLUMN `replaced_by_id` INT NULL AFTER `updated_by_id`,
            ADD COLUMN `last_debug_environment_id` INT NULL AFTER `replaced_by_id`;

        UPDATE `api_interface` ai
        INNER JOIN `api_interface_catalog` c
            ON c.project_id = ai.project_id AND c.name = '默认' AND c.parent_id IS NULL
        SET ai.catalog_id = c.id
        WHERE ai.catalog_id IS NULL;

        ALTER TABLE `api_interface`
            ADD CONSTRAINT `fk_api_if_catalog` FOREIGN KEY (`catalog_id`) REFERENCES `api_interface_catalog` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_api_if_src_ver` FOREIGN KEY (`source_document_version_id`) REFERENCES `knowledge_document_version` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_api_if_created_by` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_api_if_updated_by` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_api_if_replaced_by` FOREIGN KEY (`replaced_by_id`) REFERENCES `api_interface` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_api_if_last_debug_env` FOREIGN KEY (`last_debug_environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
            ADD KEY `idx_api_if_proj_current` (`project_id`, `is_current`),
            ADD KEY `idx_api_if_cat_sort` (`catalog_id`, `sort_order`);

        CREATE TABLE IF NOT EXISTS `api_interface_debug_template` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `payload` JSON,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `interface_id` INT NOT NULL UNIQUE,
    `default_file_id` INT,
    CONSTRAINT `fk_api_dbg_tpl_iface` FOREIGN KEY (`interface_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_dbg_tpl_file` FOREIGN KEY (`default_file_id`) REFERENCES `env_uploaded_file` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;

        ALTER TABLE `api_dependency_group`
            ADD COLUMN `target_api_id` INT NULL UNIQUE AFTER `module_id`;

        UPDATE `api_dependency_group` g
        INNER JOIN (
            SELECT dependency_group_id, MIN(from_api_id) AS from_api_id
            FROM `api_dependency`
            GROUP BY dependency_group_id
        ) d ON d.dependency_group_id = g.id
        SET g.target_api_id = d.from_api_id
        WHERE g.target_api_id IS NULL;

        ALTER TABLE `api_dependency_group`
            ADD CONSTRAINT `fk_api_dep_grp_target` FOREIGN KEY (`target_api_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE;

        ALTER TABLE `api_dependency`
            ADD COLUMN `inference_source` VARCHAR(9) NOT NULL DEFAULT 'manual'
                COMMENT 'auto_rule: auto_rule\\nauto_ai: auto_ai\\nmanual: manual' AFTER `required`,
            ADD COLUMN `confidence` DOUBLE NULL AFTER `inference_source`,
            ADD UNIQUE KEY `uid_api_dep_grp_seq` (`dependency_group_id`, `seq`);

        ALTER TABLE `api_test_case`
            ADD COLUMN `case_kind` VARCHAR(12) NOT NULL DEFAULT 'main'
                COMMENT 'precondition: precondition\\nmain: main' AFTER `title`,
            ADD COLUMN `sort_order` INT NOT NULL DEFAULT 0 AFTER `case_kind`,
            ADD COLUMN `default_file_id` INT NULL AFTER `case_payload`,
            ADD COLUMN `updated_by_id` INT NULL AFTER `created_by_id`,
            ADD CONSTRAINT `fk_api_tc_default_file` FOREIGN KEY (`default_file_id`) REFERENCES `env_uploaded_file` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_api_tc_updated_by` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
            ADD KEY `idx_api_tc_iface_kind` (`interface_id`, `case_kind`);

        UPDATE `api_test_case` tc
        INNER JOIN (
            SELECT `interface_id`, `title`, MIN(`id`) AS keep_id, COUNT(*) AS cnt
            FROM `api_test_case`
            WHERE `interface_id` IS NOT NULL
            GROUP BY `interface_id`, `title`
            HAVING cnt > 1
        ) dup ON dup.interface_id = tc.interface_id AND dup.title = tc.title AND tc.id <> dup.keep_id
        SET tc.title = CONCAT(tc.title, ' (dup-', tc.id, ')');

        ALTER TABLE `api_test_case`
            ADD UNIQUE KEY `uid_api_tc_iface_title` (`interface_id`, `title`);

        ALTER TABLE `api_case_run_record`
            MODIFY COLUMN `api_case_id` INT NULL,
            ADD COLUMN `interface_id` INT NULL AFTER `api_case_id`,
            ADD COLUMN `run_type` VARCHAR(5) NOT NULL DEFAULT 'debug'
                COMMENT 'debug: debug\\nsuite: suite' AFTER `interface_id`,
            ADD COLUMN `triggered_by_id` INT NULL AFTER `env_snapshot_id`,
            ADD CONSTRAINT `fk_api_run_iface` FOREIGN KEY (`interface_id`) REFERENCES `api_interface` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_api_run_triggered_by` FOREIGN KEY (`triggered_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `api_case_run_record`
            DROP FOREIGN KEY `fk_api_run_triggered_by`,
            DROP FOREIGN KEY `fk_api_run_iface`,
            DROP COLUMN `triggered_by_id`,
            DROP COLUMN `run_type`,
            DROP COLUMN `interface_id`,
            MODIFY COLUMN `api_case_id` INT NOT NULL;

        ALTER TABLE `api_test_case`
            DROP INDEX `uid_api_tc_iface_title`,
            DROP FOREIGN KEY `fk_api_tc_updated_by`,
            DROP FOREIGN KEY `fk_api_tc_default_file`,
            DROP COLUMN `updated_by_id`,
            DROP COLUMN `default_file_id`,
            DROP COLUMN `sort_order`,
            DROP COLUMN `case_kind`;

        ALTER TABLE `api_dependency`
            DROP INDEX `uid_api_dep_grp_seq`,
            DROP COLUMN `confidence`,
            DROP COLUMN `inference_source`;

        ALTER TABLE `api_dependency_group`
            DROP FOREIGN KEY `fk_api_dep_grp_target`,
            DROP COLUMN `target_api_id`;

        DROP TABLE IF EXISTS `api_interface_debug_template`;

        ALTER TABLE `api_interface`
            DROP FOREIGN KEY `fk_api_if_last_debug_env`,
            DROP FOREIGN KEY `fk_api_if_replaced_by`,
            DROP FOREIGN KEY `fk_api_if_updated_by`,
            DROP FOREIGN KEY `fk_api_if_created_by`,
            DROP FOREIGN KEY `fk_api_if_src_ver`,
            DROP FOREIGN KEY `fk_api_if_catalog`,
            DROP COLUMN `last_debug_environment_id`,
            DROP COLUMN `replaced_by_id`,
            DROP COLUMN `updated_by_id`,
            DROP COLUMN `created_by_id`,
            DROP COLUMN `source_document_version_id`,
            DROP COLUMN `catalog_id`,
            DROP COLUMN `sort_order`,
            DROP COLUMN `is_current`;

        DROP TABLE IF EXISTS `api_interface_catalog`;
        """
