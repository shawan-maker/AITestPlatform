from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """API响应"""
    code: int = 200
    message: str = "success"
    data: T | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _jsonable_data(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    return data


def success(data: Any = None, message: str = "success", code: int = 200) -> dict:
    return ApiResponse(
        code=code,
        message=message,
        data=_jsonable_data(data),
    ).model_dump(mode="json")
