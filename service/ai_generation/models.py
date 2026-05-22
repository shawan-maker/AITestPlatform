from tortoise import fields, models

from service.core.enums import GenType, InputRefType, SessionStatus


class AIGenerationSession(models.Model):
    id = fields.IntField(pk=True)
    project = fields.ForeignKeyField(
        "models.Project", related_name="ai_generation_sessions", on_delete=fields.CASCADE
    )
    module = fields.ForeignKeyField(
        "models.ProjectModule",
        related_name="ai_generation_sessions",
        null=True,
        on_delete=fields.SET_NULL,
    )
    gen_type = fields.CharEnumField(GenType)
    input_ref_type = fields.CharEnumField(InputRefType, null=True)
    input_ref_id = fields.IntField(null=True)
    knowledge_document = fields.ForeignKeyField(
        "models.KnowledgeDocument",
        related_name="ai_generation_sessions",
        null=True,
        on_delete=fields.SET_NULL,
    )
    model_name = fields.CharField(max_length=100, null=True)
    prompt_hash = fields.CharField(max_length=64, null=True)
    status = fields.CharEnumField(SessionStatus, default=SessionStatus.pending)
    error_message = fields.TextField(null=True)
    created_by = fields.ForeignKeyField(
        "models.User", related_name="ai_generation_sessions", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    finished_at = fields.DatetimeField(null=True, precision=6)

    class Meta:
        table = "ai_generation_session"
