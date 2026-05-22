from tortoise import fields, models

from service.core.enums import RunStatus, SuiteCaseType, TaskSuiteType


class TestTask(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="test_tasks", on_delete=fields.CASCADE
    )
    task_name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    type = fields.CharEnumField(TaskSuiteType)
    status = fields.CharEnumField(RunStatus, default=RunStatus.pending)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_test_tasks",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "test_task"


class TestSuite(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="test_suites", on_delete=fields.CASCADE
    )
    suite_name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    type = fields.CharEnumField(TaskSuiteType)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_test_suites",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "test_suite"


class SuiteCaseRelation(models.Model):
    id = fields.IntField(pk=True)
    suite = fields.ForeignKeyField(
        "models.TestSuite", related_name="case_relations", on_delete=fields.CASCADE
    )
    case_type = fields.CharEnumField(SuiteCaseType)
    case_id = fields.IntField()
    case_order = fields.IntField()

    class Meta:
        table = "suite_case_relation"
        unique_together = (("suite_id", "case_type", "case_id"),)


class TaskSuiteRelation(models.Model):
    id = fields.IntField(pk=True)
    task = fields.ForeignKeyField(
        "models.TestTask", related_name="suite_relations", on_delete=fields.CASCADE
    )
    suite = fields.ForeignKeyField(
        "models.TestSuite", related_name="task_relations", on_delete=fields.CASCADE
    )
    suite_order = fields.IntField()

    class Meta:
        table = "task_suite_relation"
