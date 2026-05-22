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
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
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
CREATE TABLE IF NOT EXISTS `test_environment` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `env_name` VARCHAR(50) NOT NULL,
    `description` VARCHAR(255),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `project_id` INT NOT NULL,
    UNIQUE KEY `uid_test_enviro_project_3c3e7a` (`project_id`, `env_name`),
    CONSTRAINT `fk_test_env_project_8a948106` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_environment_config` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `config_group` VARCHAR(50) NOT NULL DEFAULT 'base',
    `name` VARCHAR(100) NOT NULL,
    `config_type` VARCHAR(6) NOT NULL COMMENT 'scalar: scalar\njson: json\nsecret: secret' DEFAULT 'scalar',
    `value` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `environment_id` INT NOT NULL,
    UNIQUE KEY `uid_test_enviro_environ_032404` (`environment_id`, `config_group`, `name`),
    CONSTRAINT `fk_test_env_test_env_2b96104a` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_environment_db` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL DEFAULT 'default',
    `type` VARCHAR(20) NOT NULL,
    `config` JSON,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `environment_id` INT NOT NULL,
    UNIQUE KEY `uid_test_enviro_environ_ff879a` (`environment_id`, `name`),
    CONSTRAINT `fk_test_env_test_env_4ac51b97` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_environment_snapshot` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `payload` JSON NOT NULL,
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
    `rag_type` VARCHAR(11) NOT NULL COMMENT 'requirement: requirement\napi: api',
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
    `title` VARCHAR(255) NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_hash` VARCHAR(64),
    `mime_type` VARCHAR(100),
    `file_size` BIGINT,
    `version` INT NOT NULL DEFAULT 1,
    `index_status` VARCHAR(8) NOT NULL COMMENT 'pending: pending\nindexing: indexing\nindexed: indexed\nfailed: failed\nna: na' DEFAULT 'pending',
    `index_error` LONGTEXT,
    `indexed_at` DATETIME(6),
    `linked_requirement_id` INT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `workspace_id` INT NOT NULL,
    CONSTRAINT `fk_knowledg_user_562bedd9` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_knowledg_project__433466a1` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_knowledg_project_38918291` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_knowledg_knowledg_2b753eaf` FOREIGN KEY (`workspace_id`) REFERENCES `knowledge_workspace` (`id`) ON DELETE CASCADE,
    KEY `idx_knowledge_d_project_c4195a` (`project_id`, `doc_type`, `index_status`),
    KEY `idx_knowledge_d_workspa_874e8b` (`workspace_id`, `file_hash`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `requirement_doc` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `doc_no` VARCHAR(100),
    `description` LONGTEXT,
    `priority` SMALLINT NOT NULL DEFAULT 3,
    `status` VARCHAR(9) NOT NULL COMMENT 'draft: draft\nreviewing: reviewing\napproved: approved\nrejected: rejected\nchanged: changed' DEFAULT 'draft',
    `index_status` VARCHAR(8) NOT NULL COMMENT 'pending: pending\nindexing: indexing\nindexed: indexed\nfailed: failed\nna: na' DEFAULT 'na',
    `indexed_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT NOT NULL,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `source_document_id` INT,
    UNIQUE KEY `uid_requirement_module__7f734f` (`module_id`, `doc_no`),
    CONSTRAINT `fk_requirem_user_2d6022b7` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_requirem_project__31881a93` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_requirem_project_cbbc7800` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
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
    CONSTRAINT `fk_api_depe_user_ce5cb7e2` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_depe_project__74d737f3` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_depe_project_6822d620` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
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
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `module_id` INT,
    `project_id` INT NOT NULL,
    `source_document_id` INT,
    UNIQUE KEY `uid_api_interfa_project_bf5679` (`project_id`, `method`, `path`, `version`),
    CONSTRAINT `fk_api_inte_project__f8c31ea4` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_inte_project_6b021a8e` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_inte_knowledg_6f42b61b` FOREIGN KEY (`source_document_id`) REFERENCES `knowledge_document` (`id`) ON DELETE SET NULL,
    KEY `idx_api_interfa_project_498919` (`project_id`, `summary`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_dependency` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `seq` SMALLINT NOT NULL DEFAULT 1,
    `param_map` JSON,
    `required` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `dependency_group_id` INT NOT NULL,
    `from_api_id` INT NOT NULL,
    `to_api_id` INT NOT NULL,
    CONSTRAINT `fk_api_depe_api_depe_fe28b130` FOREIGN KEY (`dependency_group_id`) REFERENCES `api_dependency_group` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_depe_api_inte_7ed48179` FOREIGN KEY (`from_api_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_depe_api_inte_7f2738a0` FOREIGN KEY (`to_api_id`) REFERENCES `api_interface` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_suite` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `suite_name` VARCHAR(255) NOT NULL,
    `description` LONGTEXT,
    `type` VARCHAR(10) NOT NULL COMMENT 'api: api\nfunctional: functional\nui: ui',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `project_id` INT NOT NULL,
    CONSTRAINT `fk_test_sui_user_7f31c4c4` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_sui_project_8addcede` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `suite_case_relation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `case_type` VARCHAR(10) NOT NULL COMMENT 'api: api\nfunctional: functional',
    `case_id` INT NOT NULL,
    `case_order` INT NOT NULL,
    `suite_id` INT NOT NULL,
    UNIQUE KEY `uid_suite_case__suite_i_ceb901` (`suite_id`, `case_type`, `case_id`),
    CONSTRAINT `fk_suite_ca_test_sui_75ea30a0` FOREIGN KEY (`suite_id`) REFERENCES `test_suite` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_task` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `task_name` VARCHAR(255) NOT NULL,
    `description` LONGTEXT,
    `type` VARCHAR(10) NOT NULL COMMENT 'api: api\nfunctional: functional\nui: ui',
    `status` VARCHAR(9) NOT NULL COMMENT 'pending: pending\nrunning: running\ncompleted: completed\nfailed: failed' DEFAULT 'pending',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `project_id` INT NOT NULL,
    CONSTRAINT `fk_test_tas_user_dc8fcdd6` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_test_tas_project_d07a36bf` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `task_suite_relation` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `suite_order` INT NOT NULL,
    `suite_id` INT NOT NULL,
    `task_id` INT NOT NULL,
    CONSTRAINT `fk_task_sui_test_sui_a27a35c9` FOREIGN KEY (`suite_id`) REFERENCES `test_suite` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_task_sui_test_tas_7516b160` FOREIGN KEY (`task_id`) REFERENCES `test_task` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `test_task_run` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `status` VARCHAR(9) NOT NULL COMMENT 'pending: pending\nrunning: running\ncompleted: completed\nfailed: failed' DEFAULT 'pending',
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
    `status` VARCHAR(9) NOT NULL COMMENT 'pending: pending\nrunning: running\ncompleted: completed\nfailed: failed' DEFAULT 'pending',
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
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `generation_session_id` INT,
    `requirement_id` INT NOT NULL,
    CONSTRAINT `fk_function_ai_gener_03375fc7` FOREIGN KEY (`generation_session_id`) REFERENCES `ai_generation_session` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_requirem_bbed64b7` FOREIGN KEY (`requirement_id`) REFERENCES `requirement_doc` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `functional_case` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `case_no` VARCHAR(100),
    `case_name` VARCHAR(255) NOT NULL,
    `priority` SMALLINT NOT NULL DEFAULT 3,
    `dimension` VARCHAR(100),
    `type` VARCHAR(10) NOT NULL COMMENT 'functional: functional\nui: ui' DEFAULT 'functional',
    `status` VARCHAR(10) NOT NULL COMMENT 'design: design\nready: ready\nsmoke: smoke\nregression: regression\nobsolete: obsolete' DEFAULT 'design',
    `content_format` VARCHAR(4) NOT NULL COMMENT 'text: text\njson: json' DEFAULT 'text',
    `preconditions` LONGTEXT,
    `test_steps` LONGTEXT,
    `test_data` LONGTEXT,
    `expected_result` LONGTEXT,
    `actual_result` LONGTEXT,
    `source` VARCHAR(6) NOT NULL COMMENT 'manual: manual\nai: ai' DEFAULT 'manual',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `created_by_id` INT NOT NULL,
    `generation_session_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    `requirement_id` INT,
    `test_point_id` INT,
    CONSTRAINT `fk_function_user_270c161b` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_function_ai_gener_1a649fc0` FOREIGN KEY (`generation_session_id`) REFERENCES `ai_generation_session` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_project__52508c7e` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_project_ec31801f` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_function_requirem_e5fc25dd` FOREIGN KEY (`requirement_id`) REFERENCES `requirement_doc` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_function_function_ddb3d8bd` FOREIGN KEY (`test_point_id`) REFERENCES `functional_test_point` (`id`) ON DELETE SET NULL
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
    `env_snapshot_id` INT,
    `environment_id` INT,
    `generation_session_id` INT,
    `interface_id` INT,
    `module_id` INT,
    `project_id` INT NOT NULL,
    CONSTRAINT `fk_api_test_api_base_dc6165ed` FOREIGN KEY (`base_case_id`) REFERENCES `api_base_case` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_user_1c668f1c` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_api_test_test_env_ab7ca1a1` FOREIGN KEY (`env_snapshot_id`) REFERENCES `test_environment_snapshot` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_test_env_f52f146f` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_ai_gener_5b57e7e6` FOREIGN KEY (`generation_session_id`) REFERENCES `ai_generation_session` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_api_inte_9c9fbbd5` FOREIGN KEY (`interface_id`) REFERENCES `api_interface` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_project__453fd7bb` FOREIGN KEY (`module_id`) REFERENCES `project_module` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_test_project_f3a162a0` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE CASCADE,
    KEY `idx_api_test_ca_project_e1f5a4` (`project_id`, `module_id`, `exec_status`),
    KEY `idx_api_test_ca_interfa_e2a30e` (`interface_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `api_case_run_record` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
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
    `api_case_id` INT NOT NULL,
    `env_snapshot_id` INT,
    `environment_id` INT,
    `suite_run_id` INT,
    CONSTRAINT `fk_api_case_api_test_f817ed87` FOREIGN KEY (`api_case_id`) REFERENCES `api_test_case` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_api_case_test_env_2b0175c5` FOREIGN KEY (`env_snapshot_id`) REFERENCES `test_environment_snapshot` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_case_test_env_6d355345` FOREIGN KEY (`environment_id`) REFERENCES `test_environment` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_api_case_test_sui_93106480` FOREIGN KEY (`suite_run_id`) REFERENCES `test_suite_run` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "65yUoneLoYCETaUZQCRyLCgESPPq9d//D0nwJGY="
)
