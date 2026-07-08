"""AI用例生成模块 - models

数据模型定义
"""
from tortoise import fields, models

from service.core.enums import GenType, InputRefType, MessageRole, MessageType, SessionStatus, SourceChannel


class AIGenerationSession(models.Model):
    """generation会话"""
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
    output_payload = fields.JSONField(null=True)
    user_prompt = fields.TextField(null=True)
    source_channel = fields.CharEnumField(
        SourceChannel, default=SourceChannel.agent_center
    )
    title = fields.CharField(max_length=200, null=True)
    created_by = fields.ForeignKeyField(
        "models.User", related_name="ai_generation_sessions", on_delete=fields.RESTRICT
    )
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)
    finished_at = fields.DatetimeField(null=True, precision=6)

    class Meta:
        """meta"""
        table = "ai_generation_session"


class AIGenerationMessage(models.Model):
    """generation消息"""
    id = fields.BigIntField(pk=True)
    session = fields.ForeignKeyField(
        "models.AIGenerationSession",
        related_name="messages",
        on_delete=fields.CASCADE,
    )
    role = fields.CharEnumField(MessageRole)
    message_type = fields.CharEnumField(MessageType, default=MessageType.text)
    tool_name = fields.CharField(max_length=100, null=True)
    content = fields.TextField()
    sequence = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True, precision=6)

    class Meta:
        """meta"""
        table = "ai_generation_message"
        indexes = (("session_id", "sequence"),)
