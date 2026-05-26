from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `test_suite`
            ADD COLUMN `module_id` INT NULL AFTER `project_id`,
            ADD COLUMN `environment_id` INT NULL AFTER `module_id`,
            ADD COLUMN `run_mode` VARCHAR(8) NOT NULL DEFAULT 'serial'
                COMMENT 'serial: serial\\nparallel: parallel' AFTER `environment_id`,
            ADD CONSTRAINT `fk_test_suite_module` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_test_suite_env` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
            ADD UNIQUE KEY `uid_test_suite_proj_name` (`project_id`, `suite_name`);

        ALTER TABLE `test_task`
            ADD COLUMN `module_id` INT NULL AFTER `project_id`,
            ADD COLUMN `environment_id` INT NULL AFTER `module_id`,
            ADD COLUMN `run_mode` VARCHAR(8) NULL
                COMMENT 'serial: serial\\nparallel: parallel' AFTER `environment_id`,
            ADD CONSTRAINT `fk_test_task_module` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_test_task_env` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
            ADD UNIQUE KEY `uid_test_task_proj_name` (`project_id`, `task_name`);

        ALTER TABLE `suite_case_relation`
            ADD COLUMN `use_dependency` BOOL NOT NULL DEFAULT 1 AFTER `case_order`;

        ALTER TABLE `api_case_run_record`
            ADD COLUMN `task_run_id` INT NULL AFTER `suite_run_id`,
            ADD COLUMN `defect_id` INT NULL AFTER `log_data`,
            ADD KEY `idx_api_case_run_task_run` (`task_run_id`);

        CREATE TABLE IF NOT EXISTS `task_case_relation` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `case_type` VARCHAR(10) NOT NULL DEFAULT 'functional'
                COMMENT 'functional: functional',
            `case_id` INT NOT NULL,
            `case_order` INT NOT NULL,
            `task_id` INT NOT NULL,
            UNIQUE KEY `uid_task_case_rel` (`task_id`, `case_type`, `case_id`),
            CONSTRAINT `fk_task_case_rel_task` FOREIGN KEY (`task_id`) REFERENCES `test_task` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `test_defect` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `title` VARCHAR(255) NOT NULL,
            `steps` LONGTEXT,
            `severity` VARCHAR(8) NOT NULL DEFAULT 'normal'
                COMMENT 'normal: normal\\nserious: serious\\ncritical: critical',
            `priority` VARCHAR(6) NOT NULL DEFAULT 'medium'
                COMMENT 'high: high\\nmedium: medium\\nlow: low',
            `status` VARCHAR(6) NOT NULL DEFAULT 'init'
                COMMENT 'init: init\\nopen: open\\nclosed: closed',
            `external_key` VARCHAR(128),
            `source_type` VARCHAR(12) NOT NULL
                COMMENT 'api_case: api_case\\nfunctional_case: functional_case',
            `source_run_id` INT NULL,
            `source_case_id` INT NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `created_by_id` INT NULL,
            `module_id` INT NULL,
            `project_id` INT NOT NULL,
            CONSTRAINT `fk_test_defect_project` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_test_defect_module` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
            CONSTRAINT `fk_test_defect_created_by` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
        ) CHARACTER SET utf8mb4;

        CREATE TABLE IF NOT EXISTS `functional_case_run_record` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `exec_result` VARCHAR(8) NOT NULL DEFAULT 'pending'
                COMMENT 'pending: pending\\npassed: passed\\nfailed: failed\\nblocked: blocked\\nskipped: skipped',
            `remark` LONGTEXT,
            `start_time` DATETIME(6),
            `end_time` DATETIME(6),
            `duration_ms` INT,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `defect_id` INT NULL,
            `functional_case_id` INT NOT NULL,
            `task_run_id` INT NOT NULL,
            `triggered_by_id` INT NULL,
            CONSTRAINT `fk_fcr_task_run` FOREIGN KEY (`task_run_id`) REFERENCES `test_task_run` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_fcr_func_case` FOREIGN KEY (`functional_case_id`) REFERENCES `functional_case` (`id`) ON DELETE CASCADE,
            CONSTRAINT `fk_fcr_defect` FOREIGN KEY (`defect_id`) REFERENCES `test_defect` (`id`) ON DELETE SET NULL,
            CONSTRAINT `fk_fcr_triggered_by` FOREIGN KEY (`triggered_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
            UNIQUE KEY `uid_fcr_task_case` (`task_run_id`, `functional_case_id`)
        ) CHARACTER SET utf8mb4;

        ALTER TABLE `api_case_run_record`
            ADD CONSTRAINT `fk_api_case_run_task_run` FOREIGN KEY (`task_run_id`) REFERENCES `test_task_run` (`id`) ON DELETE SET NULL,
            ADD CONSTRAINT `fk_api_case_run_defect` FOREIGN KEY (`defect_id`) REFERENCES `test_defect` (`id`) ON DELETE SET NULL;
    """
