"""测试管理模块 - models

数据模型定义
"""
from tortoise import fields, models

from service.core.enums import RunMode, RunStatus, SuiteCaseType, TaskSuiteType


class TestTask(models.Model):
    """测试任务"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="test_tasks", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="test_tasks",
        null=True,
        on_delete=fields.SET_NULL,
    )
    environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="test_tasks",
        null=True,
        on_delete=fields.SET_NULL,
    )
    task_name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    type = fields.CharEnumField(TaskSuiteType)
    run_mode = fields.CharEnumField(RunMode, null=True)
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
        """meta"""
        table = "test_task"
        unique_together = (("project_id", "task_name"),)


class TestSuite(models.Model):
    """测试套件"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="test_suites", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="test_suites",
        null=True,
        on_delete=fields.SET_NULL,
    )
    environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="test_suites",
        null=True,
        on_delete=fields.SET_NULL,
    )
    suite_name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    type = fields.CharEnumField(TaskSuiteType)
    run_mode = fields.CharEnumField(RunMode, default=RunMode.serial)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="created_test_suites",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "test_suite"
        unique_together = (("project_id", "suite_name"),)


class SuiteCaseRelation(models.Model):
    """套件用例关联"""
    id = fields.IntField(pk=True)
    suite = fields.ForeignKeyField(
        "models.TestSuite", related_name="case_relations", on_delete=fields.CASCADE
    )
    case_type = fields.CharEnumField(SuiteCaseType)
    case_id = fields.IntField()
    case_order = fields.IntField()
    use_dependency = fields.BooleanField(default=True)

    class Meta:
        """meta"""
        table = "suite_case_relation"
        unique_together = (("suite_id", "case_type", "case_id"),)


class TaskSuiteRelation(models.Model):
    """任务套件关联"""
    id = fields.IntField(pk=True)
    task = fields.ForeignKeyField(
        "models.TestTask", related_name="suite_relations", on_delete=fields.CASCADE
    )
    suite = fields.ForeignKeyField(
        "models.TestSuite", related_name="task_relations", on_delete=fields.CASCADE
    )
    suite_order = fields.IntField()

    class Meta:
        """meta"""
        table = "task_suite_relation"
        unique_together = (("task_id", "suite_id"),)


class TaskCaseRelation(models.Model):
    """任务用例关联"""
    id = fields.IntField(pk=True)
    task = fields.ForeignKeyField(
        "models.TestTask", related_name="case_relations", on_delete=fields.CASCADE
    )
    case_type = fields.CharEnumField(SuiteCaseType, default=SuiteCaseType.functional)
    case_id = fields.IntField()
    case_order = fields.IntField()

    class Meta:
        """meta"""
        table = "task_case_relation"
        unique_together = (("task_id", "case_type", "case_id"),)
