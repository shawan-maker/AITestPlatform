"""项目管理模块 - models

数据模型定义
"""
from tortoise import fields, models


class Project(models.Model):
    """项目"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    owner = fields.ForeignKeyField(
        "models.User", related_name="owned_projects", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "project"


class ProjectMember(models.Model):
    """项目成员"""
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="members", on_delete=fields.CASCADE
    )
    user = fields.ForeignKeyField(
        "models.User", related_name="project_memberships", on_delete=fields.CASCADE
    )
    role = fields.SmallIntField(default=1)
    status = fields.SmallIntField(default=1)
    granted_by = fields.ForeignKeyField(
        "models.User",
        related_name="granted_memberships",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "project_member"
        unique_together = (("project_id", "user_id"),)


class ProjectModule(models.Model):
    """项目模块"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="modules", on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        """meta"""
        table = "project_module"
        unique_together = (("project_id", "name"),)
