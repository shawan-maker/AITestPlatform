import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from service.core.pagination import Paginated

FUNCTION_FILE_NAME_ERROR = (
    "函数文件名须以英文字母开头、以字母或数字结尾，可含英文、数字、下划线，"
    "且不能仅为数字与下划线，如 function.py 或 function_12.py"
)
FUNCTION_FILE_PATTERN = re.compile(r"^[A-Za-z]([A-Za-z0-9_]*[A-Za-z0-9])?\.py$")


class FunctionFileCreateRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=100)
    source_code: str
    environment_ids: list[int] = Field(default_factory=list)

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str) -> str:
        if not FUNCTION_FILE_PATTERN.match(value):
            raise ValueError(FUNCTION_FILE_NAME_ERROR)
        return value


class FunctionFileUpdateRequest(BaseModel):
    file_name: str | None = Field(default=None, min_length=1, max_length=100)
    source_code: str | None = None
    environment_ids: list[int] | None = None

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str | None) -> str | None:
        if value is not None and not FUNCTION_FILE_PATTERN.match(value):
            raise ValueError(FUNCTION_FILE_NAME_ERROR)
        return value

    @model_validator(mode="after")
    def at_least_one(self):
        if (
            self.file_name is None
            and self.source_code is None
            and self.environment_ids is None
        ):
            raise ValueError("至少提供 file_name、source_code 或 environment_ids 之一")
        return self


class FunctionFileBrief(BaseModel):
    id: int
    file_name: str
    project_id: int | None
    created_by_id: int | None
    is_bound: bool
    method_names: list[str] = Field(default_factory=list)
    environment_ids: list[int] = Field(default_factory=list)
    environment_names: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class BoundEnvironmentOption(BaseModel):
    id: int
    env_name: str


class FunctionFileDetail(FunctionFileBrief):
    source_code: str


class FunctionDebugRequest(BaseModel):
    method_name: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    environment_id: int | None = Field(default=None, ge=1)


class FunctionDebugResult(BaseModel):
    success: bool
    result: Any | None = None
    print_out: str = ""
    error: str = ""
    duration_ms: int = 0


PaginatedFunctionFiles = Paginated[FunctionFileBrief]


class FunctionBindItem(BaseModel):
    function_file_id: int
    sort_order: int = 0
    file_name: str | None = None


class EnvironmentFunctionBindRequest(BaseModel):
    items: list[FunctionBindItem]


class ExportFunctionEmbed(BaseModel):
    file_name: str
    source_code: str


class FunctionValidateRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=100)
    source_code: str

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str) -> str:
        if not FUNCTION_FILE_PATTERN.match(value):
            raise ValueError(FUNCTION_FILE_NAME_ERROR)
        return value


class FunctionFileBatchDeleteRequest(BaseModel):
    file_ids: list[int] = Field(..., min_length=1, max_length=50)


class FunctionFileBatchDeleteFailure(BaseModel):
    file_id: int
    message: str


class FunctionFileBatchDeleteResult(BaseModel):
    deleted_ids: list[int]
    failures: list[FunctionFileBatchDeleteFailure]
