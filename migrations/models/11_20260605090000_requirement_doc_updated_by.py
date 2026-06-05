from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `requirement_doc` ADD COLUMN `updated_by_id` INT NULL
            AFTER `created_by_id`;
        CREATE INDEX `idx_requirement_doc_updated_by_id`
            ON `requirement_doc` (`updated_by_id`);
        ALTER TABLE `requirement_doc`
            ADD CONSTRAINT `fk_requirement_doc_updated_by_6e8a9f2b`
            FOREIGN KEY (`updated_by_id`) REFERENCES `user`(`id`)
            ON DELETE SET NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `requirement_doc` DROP FOREIGN KEY `fk_requirement_doc_updated_by_6e8a9f2b`;
        ALTER TABLE `requirement_doc` DROP INDEX `idx_requirement_doc_updated_by_id`;
        ALTER TABLE `requirement_doc` DROP COLUMN `updated_by_id`;
    """
