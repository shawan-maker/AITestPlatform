"""Persist and replay ai_generation_message rows."""

from __future__ import annotations

from service.ai_generation.models import AIGenerationMessage, AIGenerationSession
from service.ai_generation.session_schemas import AIGenerationMessageOut
from service.core.enums import MessageRole, MessageType
from service.core.exceptions import AppException


class MessageService:
    @classmethod
    async def next_sequence(cls, session_id: int) -> int:
        last = (
            await AIGenerationMessage.filter(session_id=session_id)
            .order_by("-sequence")
            .first()
        )
        return (last.sequence + 1) if last else 1

    @classmethod
    async def append(
        cls,
        session_id: int,
        *,
        role: MessageRole,
        content: str,
        message_type: MessageType = MessageType.text,
        tool_name: str | None = None,
    ) -> AIGenerationMessageOut:
        seq = await cls.next_sequence(session_id)
        row = await AIGenerationMessage.create(
            session_id=session_id,
            role=role,
            message_type=message_type,
            tool_name=tool_name,
            content=content,
            sequence=seq,
        )
        return cls._to_out(row)

    @classmethod
    def _to_out(cls, row: AIGenerationMessage) -> AIGenerationMessageOut:
        return AIGenerationMessageOut(
            id=row.id,
            session_id=row.session_id,
            role=row.role,
            message_type=row.message_type,
            tool_name=row.tool_name,
            content=row.content,
            sequence=row.sequence,
            created_at=row.created_at,
        )

    @classmethod
    async def list_messages(
        cls,
        session: AIGenerationSession,
        *,
        from_sequence: int = 1,
    ) -> list[AIGenerationMessageOut]:
        rows = await AIGenerationMessage.filter(
            session_id=session.id,
            sequence__gte=from_sequence,
        ).order_by("sequence")
        return [cls._to_out(r) for r in rows]

    @classmethod
    async def ensure_session_access(
        cls,
        session_id: int,
        user_id: int,
    ) -> AIGenerationSession:
        session = await AIGenerationSession.get_or_none(id=session_id)
        if session is None:
            raise AppException("生成会话不存在", 404)
        if session.created_by_id != user_id:
            raise AppException("无权访问该会话", 403)
        return session
