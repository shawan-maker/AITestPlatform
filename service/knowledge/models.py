from tortoise import fields, models

from service.core.enums import (
    ActualParseRoute,
    IndexStatus,
    KnowledgeDocType,
    ParseMode,
    ParseStatus,
    RagBackend,
    RagType,
)


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
    """逻辑文档：不可变属性 title / project / doc_type / parse_mode。"""

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
    parse_mode = fields.CharEnumField(ParseMode)
    title = fields.CharField(max_length=255)
    # 逻辑外键 → knowledge_document_version.id，避免与 version 表形成 ORM 环
    current_version_id = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "knowledge_document"
        unique_together = (("project_id", "title"),)
        indexes = (("project_id", "doc_type", "updated_at"),)


class KnowledgeDocumentVersion(models.Model):
    id = fields.IntField(pk=True)
    document = fields.ForeignKeyField(
        "models.KnowledgeDocument",
        related_name="versions",
        on_delete=fields.CASCADE,
    )
    version_label = fields.CharField(max_length=20)
    version_seq = fields.IntField()
    file_name = fields.CharField(max_length=255)
    file_path = fields.CharField(max_length=500, null=True)
    file_hash = fields.CharField(max_length=64, null=True)
    mime_type = fields.CharField(max_length=100, null=True)
    file_size = fields.BigIntField(null=True)
    file_expired = fields.BooleanField(default=False)
    index_status = fields.CharEnumField(IndexStatus, default=IndexStatus.pending)
    index_error = fields.TextField(null=True)
    indexed_at = fields.DatetimeField(null=True, precision=6)
    parse_status = fields.CharEnumField(ParseStatus, null=True)
    parse_error = fields.TextField(null=True)
    parse_result_path = fields.CharField(max_length=500, null=True)
    actual_parse_route = fields.CharEnumField(ActualParseRoute, null=True)
    rag_backend = fields.CharEnumField(RagBackend, null=True)
    rag_doc_id = fields.CharField(max_length=500, null=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="uploaded_knowledge_document_versions",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        table = "knowledge_document_version"
        unique_together = (
            ("document_id", "version_seq"),
            ("document_id", "version_label"),
        )
        indexes = (
            ("document_id", "index_status"),
            ("document_id", "file_hash"),
        )
