"""测试环境管理模块 - models

数据模型定义
"""
from tortoise import fields, models

from service.core.enums import ConfigType, DbType


class EnvCatalog(models.Model):
    """环境目录"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="env_catalogs", on_delete=fields.CASCADE
    )
    parent = fields.ForeignKeyField(
        "models.EnvCatalog",
        related_name="children",
        null=True,
        on_delete=fields.CASCADE,
    )
    name = fields.CharField(max_length=100)
    level = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "env_catalog"
        unique_together = (("project_id", "parent_id", "name"),)


class TestEnvironment(models.Model):
    """测试环境"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="environments", on_delete=fields.CASCADE
    )
    catalog = fields.ForeignKeyField(
        "models.EnvCatalog",
        related_name="environments",
        null=True,
        on_delete=fields.SET_NULL,
    )
    env_name = fields.CharField(max_length=50)
    description = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "test_environment"
        unique_together = (("project_id", "env_name"),)
        indexes = (("project_id",), ("catalog_id",))


class TestEnvironmentConfig(models.Model):
    """测试环境配置"""
    id = fields.IntField(pk=True)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment", related_name="configs", on_delete=fields.CASCADE
    )
    config_group = fields.CharField(max_length=50, default="base")
    name = fields.CharField(max_length=100)
    config_type = fields.CharEnumField(ConfigType, default=ConfigType.scalar)
    value = fields.TextField(null=True)
    remark = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "test_environment_config"
        unique_together = (("environment_id", "config_group", "name"),)


class DbConnection(models.Model):
    """dbconnection"""
    id = fields.IntField(pk=True)
    connection_name = fields.CharField(max_length=50, unique=True)
    server_name = fields.CharField(max_length=50)
    db_type = fields.CharEnumField(DbType)
    config = fields.JSONField()
    description = fields.CharField(max_length=255, null=True)
    project = fields.ForeignKeyField(
        "models.Project",
        related_name="db_connections",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="db_connections",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "db_connection"


class EnvironmentDbRelation(models.Model):
    """环境db关联"""
    id = fields.IntField(pk=True)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="db_relations",
        on_delete=fields.CASCADE,
    )
    db_connection = fields.ForeignKeyField(
        "models.DbConnection",
        related_name="environment_relations",
        on_delete=fields.CASCADE,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        """meta"""
        table = "environment_db_relation"
        unique_together = (("environment_id", "db_connection_id"),)


class DbConnectionTestLog(models.Model):
    """dbconnection测试log"""
    id = fields.IntField(pk=True)
    db_connection = fields.ForeignKeyField(
        "models.DbConnection",
        related_name="test_logs",
        on_delete=fields.CASCADE,
    )
    success = fields.BooleanField()
    message = fields.TextField(null=True)
    tested_by = fields.ForeignKeyField(
        "models.User",
        related_name="db_connection_tests",
        null=True,
        on_delete=fields.SET_NULL,
    )
    tested_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        """meta"""
        table = "db_connection_test_log"
        indexes = (("db_connection_id", "tested_at"),)


class EnvFunctionFile(models.Model):
    """环境函数文件"""
    id = fields.IntField(pk=True)
    file_name = fields.CharField(max_length=100, unique=True)
    source_code = fields.TextField()
    project = fields.ForeignKeyField(
        "models.Project",
        related_name="function_files",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="function_files",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "env_function_file"


class EnvironmentFunctionRelation(models.Model):
    """环境函数关联"""
    id = fields.IntField(pk=True)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment",
        related_name="function_relations",
        on_delete=fields.CASCADE,
    )
    function_file = fields.ForeignKeyField(
        "models.EnvFunctionFile",
        related_name="environment_relations",
        on_delete=fields.CASCADE,
    )
    sort_order = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        """meta"""
        table = "environment_function_relation"
        unique_together = (("environment_id", "function_file_id"),)


class TestEnvironmentSnapshot(models.Model):
    """测试环境快照"""
    id = fields.IntField(pk=True)
    environment = fields.ForeignKeyField(
        "models.TestEnvironment", related_name="snapshots", on_delete=fields.CASCADE
    )
    payload = fields.JSONField()
    payload_summary = fields.JSONField(null=True)
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
        """meta"""
        table = "test_environment_snapshot"
        indexes = (("environment_id", "is_active"),)


class ProjectGlobalConfig(models.Model):
    """项目global配置"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="global_configs", on_delete=fields.CASCADE
    )
    name = fields.CharField(max_length=100)
    config_type = fields.CharEnumField(ConfigType, default=ConfigType.scalar)
    value = fields.TextField(null=True)
    remark = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "project_global_config"
        unique_together = (("project_id", "name"),)


class EnvUploadedFile(models.Model):
    """环境uploaded文件"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="env_uploaded_files", on_delete=fields.CASCADE
    )
    file_name = fields.CharField(max_length=255)
    storage_key = fields.CharField(max_length=500)
    file_size = fields.BigIntField()
    mime_type = fields.CharField(max_length=100, null=True)
    is_deleted = fields.BooleanField(default=False)
    deleted_at = fields.DatetimeField(null=True, precision=6)
    uploaded_by = fields.ForeignKeyField(
        "models.User",
        related_name="env_uploaded_files",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "env_uploaded_file"
