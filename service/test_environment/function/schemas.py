import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from service.core.pagination import Paginated

FUNCTION_FILE_PATTERN = re.compile(r"^[A-Za-z]+_\d+\.py$")


class FunctionFileCreateRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=100)
    source_code: str
    environment_ids: list[int] = Field(default_factory=list)

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str) -> str:
        if not FUNCTION_FILE_PATTERN.match(value):
            raise ValueError("函数文件名须符合 英文_数字.py 格式，如 utils_1.py")
        return value


class FunctionFileUpdateRequest(BaseModel):
    file_name: str | None = Field(default=None, min_length=1, max_length=100)
    source_code: str | None = None

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str | None) -> str | None:
        if value is not None and not FUNCTION_FILE_PATTERN.match(value):
            raise ValueError("函数文件名须符合 英文_数字.py 格式，如 utils_1.py")
        return value

    @model_validator(mode="after")
    def at_least_one(self):
        if self.file_name is None and self.source_code is None:
            raise ValueError("至少提供 file_name 或 source_code 之一")
        return self


class FunctionFileBrief(BaseModel):
    id: int
    file_name: str
    project_id: int | None
    created_by_id: int | None
    is_bound: bool
    created_at: datetime
    updated_at: datetime


class FunctionFileDetail(FunctionFileBrief):
    source_code: str


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
            raise ValueError("函数文件名须符合 英文_数字.py 格式，如 utils_1.py")
        return value
