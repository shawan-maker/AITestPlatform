from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
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
    `index_status` VARCHAR(8) NOT NULL COMMENT 'pending: pending\\nindexing: indexing\\nparsing: parsing\\nindexed: indexed\\nfailed: failed\\nna: na' DEFAULT 'pending',
    `index_error` LONGTEXT,
    `indexed_at` DATETIME(6),
    `parse_status` VARCHAR(8) COMMENT 'pending: pending\\nparsing: parsing\\nparsed: parsed\\nfailed: failed',
    `parse_error` LONGTEXT,
    `parse_result_path` VARCHAR(500),
    `actual_parse_route` VARCHAR(13) COMMENT 'ai_text: ai_text\\nai_multimodal: ai_multimodal\\nswagger: swagger\\nopenapi: openapi\\nauto_text: auto_text',
    `rag_backend` VARCHAR(11) COMMENT 'rag_client: rag_client\\nrag_manager: rag_manager',
    `rag_doc_id` VARCHAR(500),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `created_by_id` INT,
    `document_id` INT NOT NULL,
    CONSTRAINT `fk_knowledg_knowledg_ver_doc` FOREIGN KEY (`document_id`) REFERENCES `knowledge_document` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_knowledg_user_ver_uploader` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
    UNIQUE KEY `uid_knowledg_ver_doc_seq` (`document_id`, `version_seq`),
    UNIQUE KEY `uid_knowledg_ver_doc_label` (`document_id`, `version_label`),
    KEY `idx_knowledg_ver_doc_status` (`document_id`, `index_status`),
    KEY `idx_knowledg_ver_doc_hash` (`document_id`, `file_hash`)
) CHARACTER SET utf8mb4;

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

        ALTER TABLE `knowledge_document`
            ADD COLUMN `parse_mode` VARCHAR(8) NOT NULL DEFAULT 'ai'
                COMMENT 'openapi: openapi\\nswagger: swagger\\nai: ai' AFTER `doc_type`,
            ADD COLUMN `current_version_id` INT NULL AFTER `title`;

        UPDATE `knowledge_document` d
        INNER JOIN `knowledge_document_version` v
            ON v.document_id = d.id AND v.version_seq = d.version
        SET d.current_version_id = v.id
        WHERE d.current_version_id IS NULL;

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

        ALTER TABLE `requirement_doc`
            ADD COLUMN `source_document_version_id` INT NULL AFTER `source_document_id`,
            ADD COLUMN `source_version_label` VARCHAR(20) NULL AFTER `source_document_version_id`;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `requirement_doc`
            DROP COLUMN `source_version_label`,
            DROP COLUMN `source_document_version_id`;

        ALTER TABLE `knowledge_document`
            DROP INDEX `uid_knowledg_project_title`,
            DROP INDEX `idx_knowledg_doc_proj_type_upd`,
            ADD COLUMN `file_name` VARCHAR(255) NOT NULL DEFAULT '' AFTER `title`,
            ADD COLUMN `file_path` VARCHAR(500) NOT NULL DEFAULT '' AFTER `file_name`,
            ADD COLUMN `file_hash` VARCHAR(64) NULL AFTER `file_path`,
            ADD COLUMN `mime_type` VARCHAR(100) NULL AFTER `file_hash`,
            ADD COLUMN `file_size` BIGINT NULL AFTER `mime_type`,
            ADD COLUMN `version` INT NOT NULL DEFAULT 1 AFTER `file_size`,
            ADD COLUMN `index_status` VARCHAR(8) NOT NULL DEFAULT 'pending' AFTER `version`,
            ADD COLUMN `index_error` LONGTEXT NULL AFTER `index_status`,
            ADD COLUMN `indexed_at` DATETIME(6) NULL AFTER `index_error`,
            ADD COLUMN `linked_requirement_id` INT NULL AFTER `indexed_at`,
            ADD COLUMN `created_by_id` INT NULL AFTER `linked_requirement_id`,
            ADD CONSTRAINT `fk_knowledg_user_562bedd9` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL;

        UPDATE `knowledge_document` d
        INNER JOIN `knowledge_document_version` v ON v.id = d.current_version_id
        SET
            d.file_name = v.file_name,
            d.file_path = IFNULL(v.file_path, ''),
            d.file_hash = v.file_hash,
            d.mime_type = v.mime_type,
            d.file_size = v.file_size,
            d.version = v.version_seq,
            d.index_status = v.index_status,
            d.index_error = v.index_error,
            d.indexed_at = v.indexed_at,
            d.created_by_id = v.created_by_id;

        ALTER TABLE `knowledge_document`
            DROP COLUMN `current_version_id`,
            DROP COLUMN `parse_mode`,
            ADD KEY `idx_knowledge_d_project_c4195a` (`project_id`, `doc_type`, `index_status`),
            ADD KEY `idx_knowledge_d_workspa_874e8b` (`workspace_id`, `file_hash`);

        DROP TABLE IF EXISTS `knowledge_document_version`;
        """
