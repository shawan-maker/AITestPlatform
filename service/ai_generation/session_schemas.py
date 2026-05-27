"""Canonical AI generation session DTOs shared by functional and API domains."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from service.core.enums import SessionStatus


class AIGenerationSessionOut(BaseModel):
    id: int
    project_id: int
    module_id: int | None
    status: SessionStatus
    error_message: str | None
    output_payload: dict[str, Any] | None
    user_prompt: str | None
    created_at: datetime
    finished_at: datetime | None


class AIGenerationPreviewUpdateRequest(BaseModel):
    output_payload: dict[str, Any]
