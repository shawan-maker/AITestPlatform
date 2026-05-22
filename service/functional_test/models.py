from tortoise import fields, models

from service.core.enums import (
    ContentFormat,
    FunctionalCaseStatus,
    FunctionalCaseType,
    IndexStatus,
    RequirementStatus,
    SourceType,
)


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
    source_document = fields.ForeignKeyField(
        "models.KnowledgeDocument",
        related_name="synced_requirements",
        null=True,
        on_delete=fields.SET_NULL,
    )
    index_status = fields.CharEnumField(IndexStatus, default=IndexStatus.na)
    indexed_at = fields.DatetimeField(null=True, precision=6)
    created_by = fields.ForeignKeyField(
        "models.User", related_name="created_requirements", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "requirement_doc"
        unique_together = (("module_id", "doc_no"),)


class FunctionalTestPoint(models.Model):
    id = fields.IntField(pk=True)
    requirement = fields.ForeignKeyField(
        "models.RequirementDoc",
        related_name="test_points",
        on_delete=fields.CASCADE,
    )
    type = fields.CharField(max_length=50)
    dimension = fields.CharField(max_length=100)
    test_point = fields.TextField()
    source = fields.CharEnumField(SourceType, default=SourceType.ai)
    generation_session = fields.ForeignKeyField(
        "models.AIGenerationSession",
        related_name="functional_test_points",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        table = "functional_test_point"


class FunctionalCase(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="functional_cases", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="functional_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    requirement = fields.ForeignKeyField(
        "models.RequirementDoc",
        related_name="functional_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    test_point = fields.ForeignKeyField(
        "models.FunctionalTestPoint",
        related_name="functional_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    case_no = fields.CharField(max_length=100, null=True)
    case_name = fields.CharField(max_length=255)
    priority = fields.SmallIntField(default=3)
    dimension = fields.CharField(max_length=100, null=True)
    type = fields.CharEnumField(FunctionalCaseType, default=FunctionalCaseType.functional)
    status = fields.CharEnumField(
        FunctionalCaseStatus, default=FunctionalCaseStatus.design
    )
    content_format = fields.CharEnumField(ContentFormat, default=ContentFormat.text)
    preconditions = fields.TextField(null=True)
    test_steps = fields.TextField(null=True)
    test_data = fields.TextField(null=True)
    expected_result = fields.TextField(null=True)
    actual_result = fields.TextField(null=True)
    source = fields.CharEnumField(SourceType, default=SourceType.manual)
    generation_session = fields.ForeignKeyField(
        "models.AIGenerationSession",
        related_name="functional_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_by = fields.ForeignKeyField(
        "models.User", related_name="created_functional_cases", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "functional_case"
