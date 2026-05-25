from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `db_connection` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `connection_name` VARCHAR(50) NOT NULL UNIQUE,
    `server_name` VARCHAR(50) NOT NULL,
    `db_type` VARCHAR(9) NOT NULL COMMENT 'mysql: mysql\nsqlserver: sqlserver\noracle: oracle',
    `config` JSON NOT NULL,
    `description` VARCHAR(255),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `project_id` INT,
    CONSTRAINT `fk_db_conne_user_81282942` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_db_conne_project_f5fa4504` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `db_connection_test_log` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `success` BOOL NOT NULL,
    `message` LONGTEXT,
    `tested_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `db_connection_id` INT NOT NULL,
    `tested_by_id` INT,
    CONSTRAINT `fk_db_conne_db_conne_0b27b2b0` FOREIGN KEY (`db_connection_id`) REFERENCES `db_connection` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_db_conne_user_29e90ecc` FOREIGN KEY (`tested_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    KEY `idx_db_connecti_db_conn_5436c7` (`db_connection_id`, `tested_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `debug_runtime_var` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `var_key` VARCHAR(100) NOT NULL,
    `var_value` LONGTEXT,
    `source` VARCHAR(6) NOT NULL COMMENT 'engine: engine\nmanual: manual' DEFAULT 'engine',
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `environment_id` INT NOT NULL,
    `updated_by_id` INT,
    UNIQUE KEY `uid_debug_runti_environ_aebb52` (`environment_id`, `var_key`),
    CONSTRAINT `fk_debug_ru_test_env_0e1322e5` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_debug_ru_user_6e8f591a` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `env_catalog` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `level` INT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `parent_id` INT,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_env_catalog_project_b0304a` (`project_id`, `parent_id`, `name`),
    CONSTRAINT `fk_env_cata_env_cata_aa5ffb58` FOREIGN KEY (`parent_id`) REFERENCES `env_catalog` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_env_cata_project_c31119e7` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `env_function_file` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `file_name` VARCHAR(100) NOT NULL UNIQUE,
    `source_code` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `project_id` INT,
    CONSTRAINT `fk_env_func_user_74f82ef3` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_env_func_project_931b0807` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `env_uploaded_file` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `file_name` VARCHAR(255) NOT NULL,
    `storage_key` VARCHAR(500) NOT NULL,
    `file_size` BIGINT NOT NULL,
    `mime_type` VARCHAR(100),
    `is_deleted` BOOL NOT NULL DEFAULT 0,
    `deleted_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `project_id` INT NOT NULL,
    `uploaded_by_id` INT,
    CONSTRAINT `fk_env_uplo_project_d7db930a` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_env_uplo_user_c6599f5f` FOREIGN KEY (`uploaded_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `environment_db_relation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `db_connection_id` INT NOT NULL,
    `environment_id` INT NOT NULL,
    UNIQUE KEY `uid_environment_environ_befa3e` (`environment_id`, `db_connection_id`),
    CONSTRAINT `fk_environm_db_conne_73e5de16` FOREIGN KEY (`db_connection_id`) REFERENCES `db_connection` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_environm_test_env_1881fc8b` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `environment_function_relation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `sort_order` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `environment_id` INT NOT NULL,
    `function_file_id` INT NOT NULL,
    UNIQUE KEY `uid_environment_environ_902d71` (`environment_id`, `function_file_id`),
    CONSTRAINT `fk_environm_test_env_47de947a` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_environm_env_func_eb2f7d48` FOREIGN KEY (`function_file_id`) REFERENCES `env_function_file` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        ALTER TABLE `test_environment` ADD `catalog_id` INT;
        ALTER TABLE `test_environment_config` ADD `remark` VARCHAR(255);
        ALTER TABLE `test_environment_snapshot` ADD `payload_summary` JSON;
        DROP TABLE IF EXISTS `test_environment_db`;
        ALTER TABLE `test_environment` ADD CONSTRAINT `fk_test_env_env_cata_38dd2367` FOREIGN KEY (`catalog_id`) REFERENCES `env_catalog` (`id`) ON DELETE SET NULL;
        ALTER TABLE `test_environment` ADD INDEX `idx_test_enviro_project_8fe302` (`project_id`);
        ALTER TABLE `test_environment` ADD INDEX `idx_test_enviro_catalog_294e30` (`catalog_id`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `test_environment` DROP INDEX `idx_test_enviro_catalog_294e30`;
        ALTER TABLE `test_environment` DROP INDEX `idx_test_enviro_project_8fe302`;
        ALTER TABLE `test_environment` DROP FOREIGN KEY `fk_test_env_env_cata_38dd2367`;
        ALTER TABLE `test_environment` DROP COLUMN `catalog_id`;
        ALTER TABLE `test_environment_config` DROP COLUMN `remark`;
        ALTER TABLE `test_environment_snapshot` DROP COLUMN `payload_summary`;
        DROP TABLE IF EXISTS `debug_runtime_var`;
        DROP TABLE IF EXISTS `env_uploaded_file`;
        DROP TABLE IF EXISTS `environment_function_relation`;
        DROP TABLE IF EXISTS `db_connection_test_log`;
        DROP TABLE IF EXISTS `env_function_file`;
        DROP TABLE IF EXISTS `environment_db_relation`;
        DROP TABLE IF EXISTS `db_connection`;
        DROP TABLE IF EXISTS `env_catalog`;"""


MODELS_STATE = (
    "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"
    "QoDI917//H/DTxUj"
)
