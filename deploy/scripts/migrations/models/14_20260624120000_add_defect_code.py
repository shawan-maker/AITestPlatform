from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `test_defect` ADD COLUMN `defect_code` VARCHAR(32) UNIQUE NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `test_defect` DROP COLUMN `defect_code`;
    """
