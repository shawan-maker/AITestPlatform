from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ai_generation_session` ADD COLUMN `output_language` VARCHAR(5) NOT NULL DEFAULT 'zh';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ai_generation_session` DROP COLUMN `output_language`;
    """
