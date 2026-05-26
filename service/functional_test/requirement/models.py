from tortoise import fields, models

from service.core.enums import IndexStatus, RequirementSourceType, RequirementStatus


class RequirementCandidate(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="requirement_candidates", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="requirement_candidates",
        null=True,
        on_delete=fields.SET_NULL,
    )
    title = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    source_document = fields.ForeignKeyField(
        "models.KnowledgeDocument",
        related_name="requirement_candidates",
        on_delete=fields.CASCADE,
    )
    source_document_version_id = fields.IntField()
    source_version_label = fields.CharField(max_length=20)
    index_status = fields.CharEnumField(IndexStatus, default=IndexStatus.indexed)
    indexed_at = fields.DatetimeField(null=True, precision=6)
    created_by = fields.ForeignKeyField(
        "models.User", related_name="created_requirement_candidates", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "requirement_candidate"
        unique_together = (("source_document_id", "source_document_version_id"),)


class RequirementDoc(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="requirement_docs", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="requirement_docs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    title = fields.CharField(max_length=255)
    doc_no = fields.CharField(max_length=100, null=True)
    description = fields.TextField(null=True)
    priority = fields.SmallIntField(default=3)
    status = fields.CharEnumField(RequirementStatus, default=RequirementStatus.draft)
    source_type = fields.CharEnumField(
        RequirementSourceType, default=RequirementSourceType.manual
    )
    source_document = fields.ForeignKeyField(
        "models.KnowledgeDocument",
        related_name="synced_requirements",
        null=True,
        on_delete=fields.SET_NULL,
    )
    source_document_version_id = fields.IntField(null=True)
    source_version_label = fields.CharField(max_length=20, null=True)
    index_status = fields.CharEnumField(IndexStatus, default=IndexStatus.na)
    indexed_at = fields.DatetimeField(null=True, precision=6)
    created_by = fields.ForeignKeyField(
        "models.User", related_name="created_requirements", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "requirement_doc"
        unique_together = (("module_id", "doc_no"), ("project_id", "title"))
