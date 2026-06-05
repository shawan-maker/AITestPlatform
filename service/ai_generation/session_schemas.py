"""Canonical AI generation session DTOs shared by functional and API domains."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from service.core.enums import GenType, MessageRole, MessageType, SessionStatus, SourceChannel


class AIGenerationSessionOut(BaseModel):
    id: int
    project_id: int
    module_id: int | None
    gen_type: GenType
    status: SessionStatus
    error_message: str | None
    output_payload: dict[str, Any] | None
    user_prompt: str | None
    source_channel: SourceChannel
    title: str | None
    created_at: datetime
    finished_at: datetime | None


class AIGenerationSessionListItem(BaseModel):
    id: int
    project_id: int
    gen_type: GenType
    status: SessionStatus
    title: str | None
    created_at: datetime
    finished_at: datetime | None


class AIGenerationMessageOut(BaseModel):
    id: int
    session_id: int
    role: MessageRole
    message_type: MessageType
    tool_name: str | None
    content: str
    sequence: int
    created_at: datetime


class AIGenerationPreviewUpdateRequest(BaseModel):
    output_payload: dict[str, Any]


class AgentMessageRequest(BaseModel):
    content: str


class SessionRenameRequest(BaseModel):
    title: str
