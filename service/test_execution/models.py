from tortoise import fields, models

from service.core.enums import CaseRunStatus, CaseRunType, RunStatus


class ApiCaseRunRecord(models.Model):
    id = fields.IntField(pk=True)
    suite_run = fields.ForeignKeyField(
        "models.TestSuiteRun",
        related_name="case_run_records",
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
