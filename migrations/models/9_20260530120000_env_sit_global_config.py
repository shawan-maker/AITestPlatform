from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `project_global_config` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `project_id` INT NOT NULL,
            `name` VARCHAR(100) NOT NULL,
            `config_type` VARCHAR(10) NOT NULL DEFAULT 'scalar',
            `value` LONGTEXT NULL,
            `remark` VARCHAR(255) NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            CONSTRAINT `fk_project_g_project_8a1b2c3d` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
            UNIQUE KEY `uidx_project_global_config_project_name` (`project_id`, `name`)
        ) CHARACTER SET utf8mb4;

        DROP TABLE IF EXISTS `debug_runtime_var`;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `project_global_config`;

        CREATE TABLE IF NOT EXISTS `debug_runtime_var` (
            `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `environment_id` INT NOT NULL,
            `var_key` VARCHAR(100) NOT NULL,
            `var_value` LONGTEXT NULL,
            `source` VARCHAR(10) NOT NULL DEFAULT 'engine',
            `updated_by_id` INT NULL,
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            CONSTRAINT `fk_debug_ru_test_env_9f8e7d6c` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE CASCADE,
            UNIQUE KEY `uidx_debug_runtime_var_env_key` (`environment_id`, `var_key`)
        ) CHARACTER SET utf8mb4;
        """
