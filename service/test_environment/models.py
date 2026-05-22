from tortoise import fields, models

from service.core.enums import ConfigType


class TestEnvironment(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="environments", on_delete=fields.CASCADE
    )
    env_name = fields.CharField(max_length=50)
    description = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "test_environment"
        unique_together = (("project_id", "env_name"),)


class TestEnvironmentConfig(models.Model):
    id = fields.IntField(pk=True)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment", related_name="configs", on_delete=fields.CASCADE
    )
    config_group = fields.CharField(max_length=50, default="base")
    name = fields.CharField(max_length=100)
    config_type = fields.CharEnumField(ConfigType, default=ConfigType.scalar)
    value = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "test_environment_config"
        unique_together = (("environment_id", "config_group", "name"),)


class TestEnvironmentDb(models.Model):
    id = fields.IntField(pk=True)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment", related_name="databases", on_delete=fields.CASCADE
    )
    name = fields.CharField(max_length=50, default="default")
    type = fields.CharField(max_length=20)
    config = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "test_environment_db"
        unique_together = (("environment_id", "name"),)


class TestEnvironmentSnapshot(models.Model):
    id = fields.IntField(pk=True)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment", related_name="snapshots", on_delete=fields.CASCADE
    )
    payload = fields.JSONField()
    version = fields.IntField(default=1)
    is_active = fields.BooleanField(default=False)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="environment_snapshots",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        table = "test_environment_snapshot"
        indexes = (("environment_id", "is_active"),)
