from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_requirement_doc_source_01"
        ON "requirement_doc" ("source_document_id", "source_document_version_id")
        WHERE "source_document_id" IS NOT NULL AND "source_document_version_id" IS NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_requirement_doc_source_01";
    """
