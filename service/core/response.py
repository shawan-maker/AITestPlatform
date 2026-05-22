from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def success(data: Any = None, message: str = "success", code: int = 200) -> dict:
    return ApiResponse(code=code, message=message, data=data).model_dump(mode="json")
