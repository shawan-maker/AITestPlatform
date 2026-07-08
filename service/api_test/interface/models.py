"""接口测试模块 - interface/models

数据模型定义
"""
from tortoise import fields, models

from service.core.enums import ApiInterfaceSource


class ApiInterfaceCatalog(models.Model):
    """API接口目录"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="api_interface_catalogs", on_delete=fields.CASCADE
    )
    parent = fields.ForeignKeyField(
        "models.ApiInterfaceCatalog",
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
        table = "api_interface_catalog"
        unique_together = (("project_id", "parent_id", "name"),)


class ApiInterface(models.Model):
    """API接口"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="api_interfaces", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="api_interfaces",
        null=True,
        on_delete=fields.SET_NULL,
    )
    catalog = fields.ForeignKeyField(
        "models.ApiInterfaceCatalog",
        related_name="interfaces",
        null=True,
        on_delete=fields.SET_NULL,
    )
    method = fields.CharField(max_length=10)
    path = fields.CharField(max_length=255)
    summary = fields.CharField(max_length=255, null=True)
    parameters = fields.JSONField()
    request_body = fields.JSONField(null=True)
    responses = fields.JSONField()
    source = fields.CharEnumField(ApiInterfaceSource, default=ApiInterfaceSource.manual)
    source_document = fields.ForeignKeyField(
        "models.KnowledgeDocument",
        related_name="imported_api_interfaces",
        null=True,
        on_delete=fields.SET_NULL,
    )
    source_document_version = fields.ForeignKeyField(
        "models.KnowledgeDocumentVersion",
        related_name="imported_api_interfaces",
        null=True,
        on_delete=fields.SET_NULL,
    )
    version = fields.IntField(default=1)
    is_current = fields.BooleanField(default=True)
    sort_order = fields.IntField(default=0)
    replaced_by = fields.ForeignKeyField(
        "models.ApiInterface",
        related_name="replaces",
        null=True,
        on_delete=fields.SET_NULL,
    )
    last_debug_environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="last_debugged_api_interfaces",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_api_interfaces",
        null=True,
        on_delete=fields.SET_NULL,
    )
    updated_by = fields.ForeignKeyField(
        "models.User",
        related_name="updated_api_interfaces",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "api_interface"
        unique_together = (("project_id", "method", "path", "version"),)
        indexes = (
            ("project_id", "summary"),
            ("project_id", "is_current"),
            ("catalog_id", "sort_order"),
        )


class ApiInterfaceDebugTemplate(models.Model):
    """API接口调试template"""
    id = fields.IntField(pk=True)
    interface = fields.OneToOneField(
        "models.ApiInterface",
        related_name="debug_template",
        on_delete=fields.CASCADE,
    )
    payload = fields.JSONField(null=True)
    default_file = fields.ForeignKeyField(
        "models.EnvUploadedFile",
        related_name="debug_templates",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "api_interface_debug_template"
