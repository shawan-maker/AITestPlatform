from tortoise import fields, models

from service.core.enums import (
    ApiBaseCaseStatus,
    ApiInterfaceSource,
    ApiTestCaseType,
    ExecStatus,
    ReviewStatus,
    SourceType,
)


class ApiInterface(models.Model):
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
    version = fields.IntField(default=1)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "api_interface"
        unique_together = (("project_id", "method", "path", "version"),)
        indexes = (("project_id", "summary"),)


class ApiDependencyGroup(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    project = fields.ForeignKeyField(
        "models.Project", related_name="api_dependency_groups", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="api_dependency_groups",
        null=True,
        on_delete=fields.SET_NULL,
    )
    description = fields.TextField(null=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_api_dependency_groups",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "api_dependency_group"


class ApiDependency(models.Model):
    id = fields.IntField(pk=True)
    dependency_group = fields.ForeignKeyField(
        "models.ApiDependencyGroup",
        related_name="dependencies",
        on_delete=fields.CASCADE,
    )
    from_api = fields.ForeignKeyField(
        "models.ApiInterface",
        related_name="outgoing_dependencies",
        on_delete=fields.CASCADE,
    )
    to_api = fields.ForeignKeyField(
        "models.ApiInterface",
        related_name="incoming_dependencies",
        on_delete=fields.CASCADE,
    )
    seq = fields.SmallIntField(default=1)
    param_map = fields.JSONField(null=True)
    required = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        table = "api_dependency"


class ApiBaseCase(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="api_base_cases", on_delete=fields.CASCADE
    )
    interface = fields.ForeignKeyField(
        "models.ApiInterface", related_name="base_cases", on_delete=fields.CASCADE
    )
    name = fields.CharField(max_length=255)
    steps = fields.JSONField()
    dependencies = fields.JSONField(null=True)
    expected = fields.JSONField()
    status = fields.CharEnumField(ApiBaseCaseStatus, default=ApiBaseCaseStatus.draft)
    source = fields.CharEnumField(SourceType, default=SourceType.ai)
    generation_session = fields.ForeignKeyField(
        "models.AIGenerationSession",
        related_name="api_base_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_by = fields.ForeignKeyField(
        "models.User", related_name="created_api_base_cases", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "api_base_case"


class ApiTestCase(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="api_test_cases", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="api_test_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    base_case = fields.ForeignKeyField(
        "models.ApiBaseCase",
        related_name="runnable_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    interface = fields.ForeignKeyField(
        "models.ApiInterface",
        related_name="test_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    title = fields.CharField(max_length=255)
    case_payload = fields.JSONField()
    type = fields.CharEnumField(ApiTestCaseType, default=ApiTestCaseType.api)
    review_status = fields.CharEnumField(ReviewStatus, default=ReviewStatus.init)
    exec_status = fields.CharEnumField(ExecStatus, default=ExecStatus.pending)
    generation_count = fields.IntField(default=1)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="generated_api_test_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    env_snapshot = fields.ForeignKeyField(
        "models.TestEnvironmentSnapshot",
        related_name="generated_api_test_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    generation_session = fields.ForeignKeyField(
        "models.AIGenerationSession",
        related_name="api_test_cases",
        null=True,
        on_delete=fields.SET_NULL,
    )
    last_run_at = fields.DatetimeField(null=True, precision=6)
    created_by = fields.ForeignKeyField(
        "models.User", related_name="created_api_test_cases", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "api_test_case"
        indexes = (
            ("project_id", "module_id", "exec_status"),
            ("interface_id",),
        )
