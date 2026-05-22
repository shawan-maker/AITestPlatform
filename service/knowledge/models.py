from tortoise import fields, models

from service.core.enums import IndexStatus, KnowledgeDocType, RagType


class KnowledgeWorkspace(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="knowledge_workspaces", on_delete=fields.CASCADE
    )
    workspace_key = fields.CharField(max_length=100)
    rag_type = fields.CharEnumField(RagType)
    storage_path = fields.CharField(max_length=500, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "knowledge_workspace"
        unique_together = (("project_id", "rag_type"),)


class KnowledgeDocument(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="knowledge_documents", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="knowledge_documents",
        null=True,
        on_delete=fields.SET_NULL,
    )
    workspace = fields.ForeignKeyField(
        "models.KnowledgeWorkspace",
        related_name="documents",
        on_delete=fields.CASCADE,
    )
    doc_type = fields.CharEnumField(KnowledgeDocType)
    title = fields.CharField(max_length=255)
    file_name = fields.CharField(max_length=255)
    file_path = fields.CharField(max_length=500)
    file_hash = fields.CharField(max_length=64, null=True)
    mime_type = fields.CharField(max_length=100, null=True)
    file_size = fields.BigIntField(null=True)
    version = fields.IntField(default=1)
    index_status = fields.CharEnumField(IndexStatus, default=IndexStatus.pending)
    index_error = fields.TextField(null=True)
    indexed_at = fields.DatetimeField(null=True, precision=6)
    # 逻辑外键 → requirement_doc.id；不用 ForeignKeyField 以避免与 source_document 形成环
    linked_requirement_id = fields.IntField(null=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="uploaded_knowledge_documents",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "knowledge_document"
        indexes = (
            ("project_id", "doc_type", "index_status"),
            ("workspace_id", "file_hash"),
        )
