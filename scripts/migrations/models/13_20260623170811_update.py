from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `api_test_case` DROP INDEX `uid_api_tc_iface_title`;
        ALTER TABLE `api_test_case` ADD UNIQUE INDEX `uid_api_tc_iface_kind_title` (`interface_id`, `case_kind`, `title`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `api_test_case` DROP INDEX `uid_api_tc_iface_kind_title`;
        ALTER TABLE `api_test_case` ADD UNIQUE INDEX `uid_api_tc_iface_title` (`interface_id`, `title`);"""
