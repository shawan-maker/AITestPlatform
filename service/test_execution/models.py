from tortoise import fields, models

from service.core.enums import (
    CaseRunStatus,
    CaseRunType,
    DefectCategory,
    DefectHistoryAction,
    DefectPriority,
    DefectSeverity,
    DefectSourceType,
    DefectStatus,
    FunctionalExecResult,
    RunStatus,
)


class ApiCaseRunRecord(models.Model):
    id = fields.IntField(pk=True)
    suite_run = fields.ForeignKeyField(
        "models.TestSuiteRun",
        related_name="case_run_records",
        null=True,
        on_delete=fields.SET_NULL,
    )
    task_run = fields.ForeignKeyField(
        "models.TestTaskRun",
        related_name="api_case_run_records",
        null=True,
        on_delete=fields.SET_NULL,
    )
    api_case = fields.ForeignKeyField(
        "models.ApiTestCase",
        related_name="run_records",
        null=True,
        on_delete=fields.CASCADE,
    )
    interface = fields.ForeignKeyField(
        "models.ApiInterface",
        related_name="run_records",
        null=True,
        on_delete=fields.SET_NULL,
    )
    run_type = fields.CharEnumField(CaseRunType, default=CaseRunType.debug)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="case_run_records",
        null=True,
        on_delete=fields.SET_NULL,
    )
    env_snapshot = fields.ForeignKeyField(
        "models.TestEnvironmentSnapshot",
        related_name="case_run_records",
        null=True,
        on_delete=fields.SET_NULL,
    )
    triggered_by = fields.ForeignKeyField(
        "models.User",
        related_name="triggered_api_case_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    case_name = fields.CharField(max_length=255)
    status = fields.CharEnumField(CaseRunStatus)
    case_snapshot = fields.JSONField(null=True)
    error_message = fields.TextField(null=True)
    traceback = fields.TextField(null=True)
    start_time = fields.DatetimeField(null=True, precision=6)
    end_time = fields.DatetimeField(null=True, precision=6)
    duration_ms = fields.IntField(null=True)
    log_data = fields.TextField(null=True)
    api_requests_info = fields.JSONField(null=True)
    defect = fields.ForeignKeyField(
        "models.TestDefect",
        related_name="api_case_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        table = "api_case_run_record"


class TestSuiteRun(models.Model):
    id = fields.IntField(pk=True)
    suite = fields.ForeignKeyField(
        "models.TestSuite", related_name="run_records", on_delete=fields.CASCADE
    )
    run_task = fields.ForeignKeyField(
        "models.TestTaskRun",
        related_name="suite_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="suite_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    env_snapshot = fields.ForeignKeyField(
        "models.TestEnvironmentSnapshot",
        related_name="suite_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    triggered_by = fields.ForeignKeyField(
        "models.User",
        related_name="triggered_suite_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    status = fields.CharEnumField(RunStatus, default=RunStatus.pending)
    total_cases = fields.IntField(default=0)
    passed_cases = fields.IntField(default=0)
    failed_cases = fields.IntField(default=0)
    error_cases = fields.IntField(default=0)
    skipped_cases = fields.IntField(default=0)
    start_time = fields.DatetimeField(null=True, precision=6)
    end_time = fields.DatetimeField(null=True, precision=6)
    duration_ms = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "test_suite_run"


class TestTaskRun(models.Model):
    id = fields.IntField(pk=True)
    task = fields.ForeignKeyField(
        "models.TestTask", related_name="run_records", on_delete=fields.CASCADE
    )
    environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="task_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    env_snapshot = fields.ForeignKeyField(
        "models.TestEnvironmentSnapshot",
        related_name="task_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    triggered_by = fields.ForeignKeyField(
        "models.User",
        related_name="triggered_task_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    status = fields.CharEnumField(RunStatus, default=RunStatus.pending)
    total_suites = fields.IntField(default=0)
    total_cases = fields.IntField(default=0)
    passed_cases = fields.IntField(default=0)
    failed_cases = fields.IntField(default=0)
    error_cases = fields.IntField(default=0)
    skipped_cases = fields.IntField(default=0)
    start_time = fields.DatetimeField(null=True, precision=6)
    end_time = fields.DatetimeField(null=True, precision=6)
    duration_ms = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "test_task_run"


class FunctionalCaseRunRecord(models.Model):
    id = fields.IntField(pk=True)
    task_run = fields.ForeignKeyField(
        "models.TestTaskRun",
        related_name="functional_case_run_records",
        null=True,
        on_delete=fields.SET_NULL,
    )
    functional_case = fields.ForeignKeyField(
        "models.FunctionalCase",
        related_name="run_records",
        on_delete=fields.CASCADE,
    )
    exec_result = fields.CharEnumField(
        FunctionalExecResult, default=FunctionalExecResult.pending
    )
    remark = fields.TextField(null=True)
    defect = fields.ForeignKeyField(
        "models.TestDefect",
        related_name="functional_case_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    triggered_by = fields.ForeignKeyField(
        "models.User",
        related_name="triggered_functional_case_runs",
        null=True,
        on_delete=fields.SET_NULL,
    )
    start_time = fields.DatetimeField(null=True, precision=6)
    end_time = fields.DatetimeField(null=True, precision=6)
    duration_ms = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        table = "functional_case_run_record"
        unique_together = (("task_run_id", "functional_case_id"),)


class TestDefect(models.Model):
    id = fields.IntField(pk=True)
    defect_code = fields.CharField(max_length=32, null=True, unique=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="test_defects", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="test_defects",
        null=True,
        on_delete=fields.SET_NULL,
    )
    title = fields.CharField(max_length=255)
    steps = fields.TextField(null=True)
    severity = fields.CharEnumField(DefectSeverity, default=DefectSeverity.normal)
    priority = fields.CharEnumField(DefectPriority, default=DefectPriority.medium)
    status = fields.CharEnumField(DefectStatus, default=DefectStatus.init)
    defect_category = fields.CharEnumField(
        DefectCategory, default=DefectCategory.other
    )
    root_cause = fields.TextField(null=True)
    external_key = fields.CharField(max_length=128, null=True)
    source_type = fields.CharEnumField(DefectSourceType)
    source_run_id = fields.IntField(null=True)
    source_case_id = fields.IntField(null=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_test_defects",
        null=True,
        on_delete=fields.SET_NULL,
    )
    assignee = fields.ForeignKeyField(
        "models.User",
        related_name="assigned_test_defects",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)
    updated_by = fields.ForeignKeyField(
        "models.User",
        related_name="updated_test_defects",
        null=True,
        on_delete=fields.SET_NULL,
    )

    class Meta:
        table = "test_defect"
        indexes = (
            ("project_id", "status"),
            ("project_id", "created_at"),
            ("assignee_id",),
        )


class TestDefectComment(models.Model):
    id = fields.IntField(pk=True)
    defect = fields.ForeignKeyField(
        "models.TestDefect",
        related_name="comments",
        on_delete=fields.CASCADE,
    )
    content = fields.TextField()
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="test_defect_comments",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        table = "test_defect_comment"
        indexes = (("defect_id", "created_at"),)


class TestDefectHistory(models.Model):
    id = fields.IntField(pk=True)
    defect = fields.ForeignKeyField(
        "models.TestDefect",
        related_name="history_records",
        on_delete=fields.CASCADE,
    )
    action = fields.CharEnumField(DefectHistoryAction)
    field_name = fields.CharField(max_length=64, null=True)
    old_value = fields.TextField(null=True)
    new_value = fields.TextField(null=True)
    operator = fields.ForeignKeyField(
        "models.User",
        related_name="test_defect_history_ops",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        table = "test_defect_history"
        indexes = (("defect_id", "created_at"),)
