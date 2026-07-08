"""功能测试模块 - case/models

数据模型定义
"""
from tortoise import fields, models

from service.core.enums import (
    CaseCategory,
    ContentFormat,
    FunctionalCaseStatus,
    SourceType,
)


class FunctionalCaseCatalog(models.Model):
    """functional用例目录"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="functional_case_catalogs", on_delete=fields.CASCADE
    )
    parent = fields.ForeignKeyField(
        "models.FunctionalCaseCatalog",
        related_name="children",
        null=True,
        on_delete=fields.CASCADE,
    )
    name = fields.CharField(max_length=100)
    level = fields.SmallIntField(default=1)
    sort_order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "functional_case_catalog"
        unique_together = (("project_id", "parent_id", "name"),)


class FunctionalTestPoint(models.Model):
    """functional测试point"""
    id = fields.IntField(pk=True)
    type = fields.CharField(max_length=50)
    dimension = fields.CharField(max_length=100)
    test_point = fields.TextField()
    source = fields.CharEnumField(SourceType, default=SourceType.ai)
    requirement_id = fields.IntField(null=True)  # MySQL兼容：数据库残留列，允许NULL
    generation_session = fields.ForeignKeyField(
        "models.AIGenerationSession",
        related_name="functional_test_points",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        """meta"""
        table = "functional_test_point"


class FunctionalCase(models.Model):
    """functional用例"""
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
    catalog = fields.ForeignKeyField(
        "models.FunctionalCaseCatalog",
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
    case_category = fields.CharEnumField(CaseCategory, default=CaseCategory.functional)
    status = fields.CharEnumField(
        FunctionalCaseStatus, default=FunctionalCaseStatus.design
    )
    content_format = fields.CharEnumField(ContentFormat, default=ContentFormat.text)
    preconditions = fields.TextField(null=True)
    test_steps = fields.TextField(null=True)
    test_data = fields.TextField(null=True)
    expected_result = fields.TextField(null=True)
    sort_order = fields.IntField(default=0)
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
    updated_by = fields.ForeignKeyField(
        "models.User",
        related_name="updated_functional_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "functional_case"
