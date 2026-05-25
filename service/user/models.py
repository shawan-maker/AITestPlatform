from tortoise import fields, models


class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    email = fields.CharField(max_length=100, unique=True)
    password_hash = fields.CharField(max_length=60)
    is_super_admin = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
    is_deleted = fields.BooleanField(default=False)
    deleted_at = fields.DatetimeField(null=True, precision=6)
    deleted_by = fields.ForeignKeyField(
        "models.User",
        related_name="deleted_users",
        null=True,
        on_delete=fields.SET_NULL,
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    updated_at = fields.DatetimeField(auto_now=True, precision=6)

    class Meta:
        table = "user"
