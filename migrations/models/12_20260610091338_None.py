from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `user` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(60) NOT NULL,
    `is_super_admin` BOOL NOT NULL DEFAULT 0,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `is_deleted` BOOL NOT NULL DEFAULT 0,
    `deleted_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `deleted_by_id` INT,
    CONSTRAINT `fk_user_user_301022e1` FOREIGN KEY (`deleted_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `project` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `description` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `owner_id` INT NOT NULL,
    CONSTRAINT `fk_project_user_8a316aca` FOREIGN KEY (`owner_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `project_member` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `role` SMALLINT NOT NULL DEFAULT 1,
    `status` SMALLINT NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `granted_by_id` INT,
    `project_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    UNIQUE KEY `uid_project_mem_project_5d4951` (`project_id`, `user_id`),
    CONSTRAINT `fk_project__user_6c42d80c` FOREIGN KEY (`granted_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_project__project_c3c4e3b1` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_project__user_86d312d3` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `project_module` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `description` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_project_mod_project_58d9b4` (`project_id`, `name`),
    CONSTRAINT `fk_project__project_a7b1ba1d` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
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
CREATE TABLE IF NOT EXISTS `project_global_config` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `config_type` VARCHAR(6) NOT NULL COMMENT 'scalar: scalar\njson: json\nsecret: secret' DEFAULT 'scalar',
    `value` LONGTEXT,
    `remark` VARCHAR(255),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_project_glo_project_53b72f` (`project_id`, `name`),
    CONSTRAINT `fk_project__project_c2a6d86a` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_environment` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `env_name` VARCHAR(50) NOT NULL,
    `description` VARCHAR(255),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `catalog_id` INT,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_test_enviro_project_3c3e7a` (`project_id`, `env_name`),
    CONSTRAINT `fk_test_env_env_cata_38dd2367` FOREIGN KEY (`catalog_id`) REFERENCES `env_catalog` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_env_project_8a948106` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    KEY `idx_test_enviro_project_8fe302` (`project_id`),
    KEY `idx_test_enviro_catalog_294e30` (`catalog_id`)
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
CREATE TABLE IF NOT EXISTS `test_environment_config` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `config_group` VARCHAR(50) NOT NULL DEFAULT 'base',
    `name` VARCHAR(100) NOT NULL,
    `config_type` VARCHAR(6) NOT NULL COMMENT 'scalar: scalar\njson: json\nsecret: secret' DEFAULT 'scalar',
    `value` LONGTEXT,
    `remark` VARCHAR(255),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `environment_id` INT NOT NULL,
    UNIQUE KEY `uid_test_enviro_environ_032404` (`environment_id`, `config_group`, `name`),
    CONSTRAINT `fk_test_env_test_env_2b96104a` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_environment_snapshot` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `payload` JSON NOT NULL,
    `payload_summary` JSON,
    `version` INT NOT NULL DEFAULT 1,
    `is_active` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `environment_id` INT NOT NULL,
    CONSTRAINT `fk_test_env_user_36d9683e` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_env_test_env_006d0ef7` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE CASCADE,
    KEY `idx_test_enviro_environ_f92a10` (`environment_id`, `is_active`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `knowledge_workspace` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `workspace_key` VARCHAR(100) NOT NULL,
    `rag_type` VARCHAR(3) NOT NULL COMMENT 'api: api',
    `storage_path` VARCHAR(500),
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_knowledge_w_project_bfafa6` (`project_id`, `rag_type`),
    CONSTRAINT `fk_knowledg_project_53a903ad` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `knowledge_document` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `doc_type` VARCHAR(11) NOT NULL COMMENT 'requirement: requirement\napi_doc: api_doc\nother: other',
    `parse_mode` VARCHAR(7) NOT NULL COMMENT 'openapi: openapi\nswagger: swagger\nai: ai',
    `title` VARCHAR(255) NOT NULL,
    `current_version_id` INT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `module_id` INT,
    `project_id` INT NOT NULL,
    `workspace_id` INT NOT NULL,
    UNIQUE KEY `uid_knowledge_d_project_f1588c` (`project_id`, `title`),
    CONSTRAINT `fk_knowledg_project__433466a1` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_knowledg_project_38918291` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_knowledg_knowledg_2b753eaf` FOREIGN KEY (`workspace_id`) REFERENCES `knowledge_workspace` (`id`) ON DELETE CASCADE,
    KEY `idx_knowledge_d_project_8ea165` (`project_id`, `doc_type`, `updated_at`)
) CHARACTER SET utf8mb4 COMMENT='逻辑文档：不可变属性 title / project / doc_type / parse_mode。';
CREATE TABLE IF NOT EXISTS `knowledge_document_version` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version_label` VARCHAR(20) NOT NULL,
    `version_seq` INT NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500),
    `file_hash` VARCHAR(64),
    `mime_type` VARCHAR(100),
    `file_size` BIGINT,
    `file_expired` BOOL NOT NULL DEFAULT 0,
    `index_status` VARCHAR(8) NOT NULL COMMENT 'pending: pending\nindexing: indexing\nparsing: parsing\nindexed: indexed\nfailed: failed\nna: na' DEFAULT 'pending',
    `index_error` LONGTEXT,
    `indexed_at` DATETIME(6),
    `parse_status` VARCHAR(7) COMMENT 'pending: pending\nparsing: parsing\nparsed: parsed\nfailed: failed',
    `parse_error` LONGTEXT,
    `parse_result_path` VARCHAR(500),
    `actual_parse_route` VARCHAR(13) COMMENT 'ai_text: ai_text\nai_multimodal: ai_multimodal\nswagger: swagger\nopenapi: openapi\nauto_text: auto_text',
    `rag_backend` VARCHAR(11) COMMENT 'rag_client: rag_client\nrag_manager: rag_manager',
    `rag_doc_id` VARCHAR(500),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `document_id` INT NOT NULL,
    UNIQUE KEY `uid_knowledge_d_documen_7f4e24` (`document_id`, `version_seq`),
    UNIQUE KEY `uid_knowledge_d_documen_6fc2a4` (`document_id`, `version_label`),
    CONSTRAINT `fk_knowledg_user_9bb9a760` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_knowledg_knowledg_006046c2` FOREIGN KEY (`document_id`) REFERENCES `knowledge_document` (`id`) ON DELETE CASCADE,
    KEY `idx_knowledge_d_documen_efb955` (`document_id`, `index_status`),
    KEY `idx_knowledge_d_documen_291428` (`document_id`, `file_hash`)
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
    UNIQUE KEY `uid_functional__project_d7e938` (`project_id`, `parent_id`, `name`),
    CONSTRAINT `fk_function_function_2a37527b` FOREIGN KEY (`parent_id`) REFERENCES `functional_case_catalog` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_function_project_5b6e98c8` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_interface_catalog` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `level` SMALLINT NOT NULL DEFAULT 1,
    `sort_order` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `parent_id` INT,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_api_interfa_project_7ec698` (`project_id`, `parent_id`, `name`),
    CONSTRAINT `fk_api_inte_api_inte_1759e430` FOREIGN KEY (`parent_id`) REFERENCES `api_interface_catalog` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_inte_project_36739b73` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_interface` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `method` VARCHAR(10) NOT NULL,
    `path` VARCHAR(255) NOT NULL,
    `summary` VARCHAR(255),
    `parameters` JSON NOT NULL,
    `request_body` JSON,
    `responses` JSON NOT NULL,
    `source` VARCHAR(7) NOT NULL COMMENT 'swagger: swagger\nopenapi: openapi\nrag: rag\nmanual: manual' DEFAULT 'manual',
    `version` INT NOT NULL DEFAULT 1,
    `is_current` BOOL NOT NULL DEFAULT 1,
    `sort_order` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `catalog_id` INT,
    `created_by_id` INT,
    `last_debug_environment_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `replaced_by_id` INT,
    `source_document_id` INT,
    `source_document_version_id` INT,
    `updated_by_id` INT,
    UNIQUE KEY `uid_api_interfa_project_bf5679` (`project_id`, `method`, `path`, `version`),
    CONSTRAINT `fk_api_inte_api_inte_bcab13fe` FOREIGN KEY (`catalog_id`) REFERENCES `api_interface_catalog` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_user_20302e76` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_test_env_27b3f92e` FOREIGN KEY (`last_debug_environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_project__f8c31ea4` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_project_6b021a8e` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_inte_api_inte_842383f3` FOREIGN KEY (`replaced_by_id`) REFERENCES `api_interface` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_knowledg_6f42b61b` FOREIGN KEY (`source_document_id`) REFERENCES `knowledge_document` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_knowledg_f22b737e` FOREIGN KEY (`source_document_version_id`) REFERENCES `knowledge_document_version` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_user_e9bf66d8` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    KEY `idx_api_interfa_project_498919` (`project_id`, `summary`),
    KEY `idx_api_interfa_project_8538f9` (`project_id`, `is_current`),
    KEY `idx_api_interfa_catalog_023393` (`catalog_id`, `sort_order`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_dependency_group` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `description` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `target_api_id` INT UNIQUE,
    CONSTRAINT `fk_api_depe_user_ce5cb7e2` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_depe_project__74d737f3` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_depe_project_6822d620` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_depe_api_inte_0c094184` FOREIGN KEY (`target_api_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_dependency` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `seq` SMALLINT NOT NULL DEFAULT 1,
    `param_map` JSON,
    `required` BOOL NOT NULL DEFAULT 1,
    `inference_source` VARCHAR(9) NOT NULL COMMENT 'auto_rule: auto_rule\nauto_ai: auto_ai\nmanual: manual' DEFAULT 'manual',
    `confidence` DOUBLE,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `dependency_group_id` INT NOT NULL,
    `from_api_id` INT NOT NULL,
    `to_api_id` INT NOT NULL,
    UNIQUE KEY `uid_api_depende_depende_4a8399` (`dependency_group_id`, `seq`),
    CONSTRAINT `fk_api_depe_api_depe_fe28b130` FOREIGN KEY (`dependency_group_id`) REFERENCES `api_dependency_group` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_depe_api_inte_7ed48179` FOREIGN KEY (`from_api_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_depe_api_inte_7f2738a0` FOREIGN KEY (`to_api_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_interface_debug_template` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `payload` JSON,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `default_file_id` INT,
    `interface_id` INT NOT NULL UNIQUE,
    CONSTRAINT `fk_api_inte_env_uplo_8ffcd64b` FOREIGN KEY (`default_file_id`) REFERENCES `env_uploaded_file` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_api_inte_1bdafbae` FOREIGN KEY (`interface_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_suite` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `suite_name` VARCHAR(255) NOT NULL,
    `description` LONGTEXT,
    `type` VARCHAR(10) NOT NULL COMMENT 'api: api\nfunctional: functional\nui: ui',
    `run_mode` VARCHAR(8) NOT NULL COMMENT 'serial: serial\nparallel: parallel' DEFAULT 'serial',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `environment_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_test_suite_project_665b1e` (`project_id`, `suite_name`),
    CONSTRAINT `fk_test_sui_user_7f31c4c4` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_sui_test_env_66cb8285` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_sui_project__9b20f02c` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_sui_project_8addcede` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `suite_case_relation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `case_type` VARCHAR(10) NOT NULL COMMENT 'api: api\nfunctional: functional',
    `case_id` INT NOT NULL,
    `case_order` INT NOT NULL,
    `use_dependency` BOOL NOT NULL DEFAULT 1,
    `suite_id` INT NOT NULL,
    UNIQUE KEY `uid_suite_case__suite_i_ceb901` (`suite_id`, `case_type`, `case_id`),
    CONSTRAINT `fk_suite_ca_test_sui_75ea30a0` FOREIGN KEY (`suite_id`) REFERENCES `test_suite` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_task` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `task_name` VARCHAR(255) NOT NULL,
    `description` LONGTEXT,
    `type` VARCHAR(10) NOT NULL COMMENT 'api: api\nfunctional: functional\nui: ui',
    `run_mode` VARCHAR(8) COMMENT 'serial: serial\nparallel: parallel',
    `status` VARCHAR(9) NOT NULL COMMENT 'pending: pending\nrunning: running\ncompleted: completed\nfailed: failed\ncancelled: cancelled' DEFAULT 'pending',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `environment_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_test_task_project_3ddd8f` (`project_id`, `task_name`),
    CONSTRAINT `fk_test_tas_user_dc8fcdd6` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_tas_test_env_6a30d310` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_tas_project__8d8686fd` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_tas_project_d07a36bf` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `task_case_relation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `case_type` VARCHAR(10) NOT NULL COMMENT 'api: api\nfunctional: functional' DEFAULT 'functional',
    `case_id` INT NOT NULL,
    `case_order` INT NOT NULL,
    `task_id` INT NOT NULL,
    UNIQUE KEY `uid_task_case_r_task_id_82b298` (`task_id`, `case_type`, `case_id`),
    CONSTRAINT `fk_task_cas_test_tas_947c8f1c` FOREIGN KEY (`task_id`) REFERENCES `test_task` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `task_suite_relation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `suite_order` INT NOT NULL,
    `suite_id` INT NOT NULL,
    `task_id` INT NOT NULL,
    UNIQUE KEY `uid_task_suite__task_id_17cd33` (`task_id`, `suite_id`),
    CONSTRAINT `fk_task_sui_test_sui_a27a35c9` FOREIGN KEY (`suite_id`) REFERENCES `test_suite` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_sui_test_tas_7516b160` FOREIGN KEY (`task_id`) REFERENCES `test_task` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_defect` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `steps` LONGTEXT,
    `severity` VARCHAR(8) NOT NULL COMMENT 'normal: normal\nserious: serious\ncritical: critical' DEFAULT 'normal',
    `priority` VARCHAR(6) NOT NULL COMMENT 'high: high\nmedium: medium\nlow: low' DEFAULT 'medium',
    `status` VARCHAR(11) NOT NULL COMMENT 'init: init\nopen: open\nin_progress: in_progress\nresolved: resolved\nclosed: closed' DEFAULT 'init',
    `defect_category` VARCHAR(13) NOT NULL COMMENT 'functional: functional\nperformance: performance\nui: ui\ncompatibility: compatibility\nsecurity: security\nother: other' DEFAULT 'other',
    `root_cause` LONGTEXT,
    `external_key` VARCHAR(128),
    `source_type` VARCHAR(15) NOT NULL COMMENT 'api_case: api_case\nfunctional_case: functional_case\nmanual: manual',
    `source_run_id` INT,
    `source_case_id` INT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `assignee_id` INT,
    `created_by_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `updated_by_id` INT,
    CONSTRAINT `fk_test_def_user_211b2b5f` FOREIGN KEY (`assignee_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_def_user_bf420460` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_def_project__c9258091` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_def_project_c3f80e60` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_test_def_user_d43da1c9` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    KEY `idx_test_defect_project_a38f2c` (`project_id`, `status`),
    KEY `idx_test_defect_project_d611b3` (`project_id`, `created_at`),
    KEY `idx_test_defect_assigne_a3fce1` (`assignee_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_defect_comment` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `content` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `defect_id` INT NOT NULL,
    CONSTRAINT `fk_test_def_user_7b3f4003` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_def_test_def_814cbd70` FOREIGN KEY (`defect_id`) REFERENCES `test_defect` (`id`) ON DELETE CASCADE,
    KEY `idx_test_defect_defect__776f66` (`defect_id`, `created_at`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_defect_history` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `action` VARCHAR(13) NOT NULL COMMENT 'status_change: status_change\nfield_update: field_update\ncomment_added: comment_added\ncreated: created',
    `field_name` VARCHAR(64),
    `old_value` LONGTEXT,
    `new_value` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `defect_id` INT NOT NULL,
    `operator_id` INT,
    CONSTRAINT `fk_test_def_test_def_9ac6e081` FOREIGN KEY (`defect_id`) REFERENCES `test_defect` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_test_def_user_2de4a8eb` FOREIGN KEY (`operator_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    KEY `idx_test_defect_defect__ca9d50` (`defect_id`, `created_at`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_task_run` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `status` VARCHAR(9) NOT NULL COMMENT 'pending: pending\nrunning: running\ncompleted: completed\nfailed: failed\ncancelled: cancelled' DEFAULT 'pending',
    `total_suites` INT NOT NULL DEFAULT 0,
    `total_cases` INT NOT NULL DEFAULT 0,
    `passed_cases` INT NOT NULL DEFAULT 0,
    `failed_cases` INT NOT NULL DEFAULT 0,
    `error_cases` INT NOT NULL DEFAULT 0,
    `skipped_cases` INT NOT NULL DEFAULT 0,
    `start_time` DATETIME(6),
    `end_time` DATETIME(6),
    `duration_ms` INT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `env_snapshot_id` INT,
    `environment_id` INT,
    `task_id` INT NOT NULL,
    `triggered_by_id` INT,
    CONSTRAINT `fk_test_tas_test_env_cdab40e8` FOREIGN KEY (`env_snapshot_id`) REFERENCES `test_environment_snapshot` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_tas_test_env_bd796b3a` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_tas_test_tas_c09dcab1` FOREIGN KEY (`task_id`) REFERENCES `test_task` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_test_tas_user_1d19a2f4` FOREIGN KEY (`triggered_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_suite_run` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `status` VARCHAR(9) NOT NULL COMMENT 'pending: pending\nrunning: running\ncompleted: completed\nfailed: failed\ncancelled: cancelled' DEFAULT 'pending',
    `total_cases` INT NOT NULL DEFAULT 0,
    `passed_cases` INT NOT NULL DEFAULT 0,
    `failed_cases` INT NOT NULL DEFAULT 0,
    `error_cases` INT NOT NULL DEFAULT 0,
    `skipped_cases` INT NOT NULL DEFAULT 0,
    `start_time` DATETIME(6),
    `end_time` DATETIME(6),
    `duration_ms` INT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `env_snapshot_id` INT,
    `environment_id` INT,
    `run_task_id` INT,
    `suite_id` INT NOT NULL,
    `triggered_by_id` INT,
    CONSTRAINT `fk_test_sui_test_env_df2165f1` FOREIGN KEY (`env_snapshot_id`) REFERENCES `test_environment_snapshot` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_sui_test_env_47c772bc` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_sui_test_tas_e9a850da` FOREIGN KEY (`run_task_id`) REFERENCES `test_task_run` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_sui_test_sui_93f50b94` FOREIGN KEY (`suite_id`) REFERENCES `test_suite` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_test_sui_user_f9ac4353` FOREIGN KEY (`triggered_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `ai_generation_session` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `gen_type` VARCHAR(12) NOT NULL COMMENT 'functional: functional\napi_base: api_base\napi_runnable: api_runnable',
    `input_ref_type` VARCHAR(11) COMMENT 'requirement: requirement\ninterface: interface\napi_doc: api_doc',
    `input_ref_id` INT,
    `model_name` VARCHAR(100),
    `prompt_hash` VARCHAR(64),
    `status` VARCHAR(7) NOT NULL COMMENT 'pending: pending\nrunning: running\nsuccess: success\nfailed: failed' DEFAULT 'pending',
    `error_message` LONGTEXT,
    `output_payload` JSON,
    `user_prompt` LONGTEXT,
    `source_channel` VARCHAR(16) NOT NULL COMMENT 'agent_center: agent_center\ninterface_detail: interface_detail\nlegacy: legacy' DEFAULT 'agent_center',
    `title` VARCHAR(200),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `finished_at` DATETIME(6),
    `created_by_id` INT NOT NULL,
    `knowledge_document_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    CONSTRAINT `fk_ai_gener_user_846abc70` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_ai_gener_knowledg_30827c2a` FOREIGN KEY (`knowledge_document_id`) REFERENCES `knowledge_document` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_ai_gener_project__0da627bf` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_ai_gener_project_15d2fe33` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `functional_test_point` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `type` VARCHAR(50) NOT NULL,
    `dimension` VARCHAR(100) NOT NULL,
    `test_point` LONGTEXT NOT NULL,
    `source` VARCHAR(6) NOT NULL COMMENT 'manual: manual\nai: ai' DEFAULT 'ai',
    `requirement_id` INT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `generation_session_id` INT,
    CONSTRAINT `fk_function_ai_gener_03375fc7` FOREIGN KEY (`generation_session_id`) REFERENCES `ai_generation_session` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `functional_case` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `case_no` VARCHAR(100),
    `case_name` VARCHAR(255) NOT NULL,
    `priority` SMALLINT NOT NULL DEFAULT 3,
    `dimension` VARCHAR(100),
    `case_category` VARCHAR(13) NOT NULL COMMENT 'functional: functional\nperformance: performance\nsecurity: security\ncompatibility: compatibility\nusability: usability\nother: other' DEFAULT 'functional',
    `status` VARCHAR(10) NOT NULL COMMENT 'design: design\nready: ready\nsmoke: smoke\nregression: regression\nobsolete: obsolete' DEFAULT 'design',
    `exec_result` VARCHAR(7) NOT NULL COMMENT 'pending: pending\npassed: passed\nfailed: failed\nblocked: blocked\nskipped: skipped' DEFAULT 'pending',
    `content_format` VARCHAR(4) NOT NULL COMMENT 'text: text\njson: json' DEFAULT 'text',
    `preconditions` LONGTEXT,
    `test_steps` LONGTEXT,
    `test_data` LONGTEXT,
    `expected_result` LONGTEXT,
    `actual_result` LONGTEXT,
    `jira_issue_key` VARCHAR(50),
    `sort_order` INT NOT NULL DEFAULT 0,
    `source` VARCHAR(6) NOT NULL COMMENT 'manual: manual\nai: ai' DEFAULT 'manual',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `catalog_id` INT,
    `created_by_id` INT NOT NULL,
    `generation_session_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `test_point_id` INT,
    `updated_by_id` INT,
    CONSTRAINT `fk_function_function_d4321918` FOREIGN KEY (`catalog_id`) REFERENCES `functional_case_catalog` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_user_270c161b` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_function_ai_gener_1a649fc0` FOREIGN KEY (`generation_session_id`) REFERENCES `ai_generation_session` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_project__52508c7e` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_project_ec31801f` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_function_function_ddb3d8bd` FOREIGN KEY (`test_point_id`) REFERENCES `functional_test_point` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_user_db3363c6` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_base_case` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL,
    `steps` JSON NOT NULL,
    `dependencies` JSON,
    `expected` JSON NOT NULL,
    `status` VARCHAR(8) NOT NULL COMMENT 'draft: draft\napproved: approved\narchived: archived' DEFAULT 'draft',
    `source` VARCHAR(6) NOT NULL COMMENT 'manual: manual\nai: ai' DEFAULT 'ai',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT NOT NULL,
    `generation_session_id` INT,
    `interface_id` INT NOT NULL,
    `project_id` INT NOT NULL,
    CONSTRAINT `fk_api_base_user_567f978a` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_api_base_ai_gener_02dd2723` FOREIGN KEY (`generation_session_id`) REFERENCES `ai_generation_session` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_base_api_inte_fc7a0116` FOREIGN KEY (`interface_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_base_project_bc15a67c` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_test_case` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `case_kind` VARCHAR(12) NOT NULL COMMENT 'precondition: precondition\nmain: main' DEFAULT 'main',
    `sort_order` INT NOT NULL DEFAULT 0,
    `case_payload` JSON NOT NULL,
    `type` VARCHAR(8) NOT NULL COMMENT 'api: api\nbusiness: business' DEFAULT 'api',
    `review_status` VARCHAR(7) NOT NULL COMMENT 'init: init\nsuccess: success\nfail: fail\nerror: error' DEFAULT 'init',
    `exec_status` VARCHAR(8) NOT NULL COMMENT 'pending: pending\nready: ready\ndisabled: disabled' DEFAULT 'pending',
    `generation_count` INT NOT NULL DEFAULT 1,
    `last_run_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `base_case_id` INT,
    `created_by_id` INT NOT NULL,
    `default_file_id` INT,
    `env_snapshot_id` INT,
    `environment_id` INT,
    `generation_session_id` INT,
    `interface_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `updated_by_id` INT,
    UNIQUE KEY `uid_api_test_ca_interfa_fee884` (`interface_id`, `title`),
    CONSTRAINT `fk_api_test_api_base_dc6165ed` FOREIGN KEY (`base_case_id`) REFERENCES `api_base_case` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_user_1c668f1c` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_api_test_env_uplo_2c967b48` FOREIGN KEY (`default_file_id`) REFERENCES `env_uploaded_file` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_test_env_ab7ca1a1` FOREIGN KEY (`env_snapshot_id`) REFERENCES `test_environment_snapshot` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_test_env_f52f146f` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_ai_gener_5b57e7e6` FOREIGN KEY (`generation_session_id`) REFERENCES `ai_generation_session` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_api_inte_9c9fbbd5` FOREIGN KEY (`interface_id`) REFERENCES `api_interface` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_project__453fd7bb` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_project_f3a162a0` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_test_user_95c241a0` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    KEY `idx_api_test_ca_project_e1f5a4` (`project_id`, `module_id`, `exec_status`),
    KEY `idx_api_test_ca_interfa_55638f` (`interface_id`, `case_kind`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_case_run_record` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `run_type` VARCHAR(5) NOT NULL COMMENT 'debug: debug\nsuite: suite' DEFAULT 'debug',
    `case_name` VARCHAR(255) NOT NULL,
    `status` VARCHAR(7) NOT NULL COMMENT 'success: success\nfail: fail\nerror: error',
    `case_snapshot` JSON,
    `error_message` LONGTEXT,
    `traceback` LONGTEXT,
    `start_time` DATETIME(6),
    `end_time` DATETIME(6),
    `duration_ms` INT,
    `log_data` LONGTEXT,
    `api_requests_info` JSON,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `api_case_id` INT,
    `defect_id` INT,
    `env_snapshot_id` INT,
    `environment_id` INT,
    `interface_id` INT,
    `suite_run_id` INT,
    `task_run_id` INT,
    `triggered_by_id` INT,
    CONSTRAINT `fk_api_case_api_test_f817ed87` FOREIGN KEY (`api_case_id`) REFERENCES `api_test_case` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_case_test_def_095f943a` FOREIGN KEY (`defect_id`) REFERENCES `test_defect` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_case_test_env_2b0175c5` FOREIGN KEY (`env_snapshot_id`) REFERENCES `test_environment_snapshot` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_case_test_env_6d355345` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_case_api_inte_6c447579` FOREIGN KEY (`interface_id`) REFERENCES `api_interface` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_case_test_sui_93106480` FOREIGN KEY (`suite_run_id`) REFERENCES `test_suite_run` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_case_test_tas_d1136b1f` FOREIGN KEY (`task_run_id`) REFERENCES `test_task_run` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_case_user_a1e99be7` FOREIGN KEY (`triggered_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `functional_case_run_record` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `exec_result` VARCHAR(7) NOT NULL COMMENT 'pending: pending\npassed: passed\nfailed: failed\nblocked: blocked\nskipped: skipped' DEFAULT 'pending',
    `remark` LONGTEXT,
    `start_time` DATETIME(6),
    `end_time` DATETIME(6),
    `duration_ms` INT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `defect_id` INT,
    `functional_case_id` INT NOT NULL,
    `task_run_id` INT NOT NULL,
    `triggered_by_id` INT,
    UNIQUE KEY `uid_functional__task_ru_d54cd1` (`task_run_id`, `functional_case_id`),
    CONSTRAINT `fk_function_test_def_366acd9d` FOREIGN KEY (`defect_id`) REFERENCES `test_defect` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_function_18d3df8d` FOREIGN KEY (`functional_case_id`) REFERENCES `functional_case` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_function_test_tas_e750b842` FOREIGN KEY (`task_run_id`) REFERENCES `test_task_run` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_function_user_54e907f8` FOREIGN KEY (`triggered_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `ai_generation_message` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `role` VARCHAR(9) NOT NULL COMMENT 'user: user\nassistant: assistant\ntool: tool\nsystem: system',
    `message_type` VARCHAR(11) NOT NULL COMMENT 'text: text\ncustom: custom\ntool_call: tool_call\ntool_result: tool_result' DEFAULT 'text',
    `tool_name` VARCHAR(100),
    `content` LONGTEXT NOT NULL,
    `sequence` INT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `session_id` INT NOT NULL,
    CONSTRAINT `fk_ai_gener_ai_gener_0f1449fc` FOREIGN KEY (`session_id`) REFERENCES `ai_generation_session` (`id`) ON DELETE CASCADE,
    KEY `idx_ai_generati_session_e7ffbd` (`session_id`, `sequence`)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
