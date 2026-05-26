from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DebugTemplateOut(BaseModel):
    interface_id: int
    payload: dict[str, Any] | None
    default_file_id: int | None
    updated_at: datetime | None


class DebugTemplateSaveRequest(BaseModel):
    payload: dict[str, Any] | None = None
    default_file_id: int | None = Field(default=None, ge=1)


class DebugRunRequest(BaseModel):
    environment_id: int = Field(..., ge=1)
    payload: dict[str, Any] | None = None
    file_id: int | None = Field(default=None, ge=1)


class DebugRunOut(BaseModel):
    run_record_id: int
    status: str
    duration_ms: int | None
