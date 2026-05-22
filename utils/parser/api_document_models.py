"""
接口文档解析结果的数据模型（仅 Pydantic，无 LLM / LangChain 依赖）。

供 swagger/openapi 解析器与 AI 解析模块共用，避免导入重型依赖。
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BodyField(BaseModel):
    """请求体字段模型"""

    name: str = Field(..., description="字段名")
    type: str = Field(..., description="字段类型")
    description: str = Field(..., description="字段说明")
    required: bool = Field(default=False, description="是否必填")
    nested_fields: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="嵌套字段，仅当type为object时存在",
    )
    array_item_fields: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="数组元素字段，仅当type为array时存在",
    )


class Parameter(BaseModel):
    """参数模型"""

    name: str = Field(..., description="参数名")
    type: str = Field(..., description="参数类型")
    description: str = Field(..., description="参数说明")
    required: bool = Field(default=False, description="是否必填")


class RequestBody(BaseModel):
    """请求体模型"""

    content_type: Optional[str] = Field(default=None, description="请求体类型")
    body: List[BodyField] = Field(default_factory=list, description="请求体字段列表")


class Response(BaseModel):
    """响应模型"""

    http_code: str = Field(..., description="HTTP状态码")
    description: str = Field(..., description="响应描述")
    media_type: str = Field(..., description="响应内容类型")
    response_body: Dict[str, Any] = Field(default_factory=dict, description="响应体示例")


class APIDocumentParserModel(BaseModel):
    """接口文档解析结果的模型"""

    path: str = Field(default="", description="API路径，必须以/开头")
    method: str = Field(
        default="",
        description="HTTP方法，必须是GET/POST/PUT/DELETE/PATCH之一",
    )
    summary: str = Field(default="", description="接口简要描述")
    parameters: Dict[str, List[Parameter]] = Field(
        default_factory=lambda: {"header": [], "path": [], "query": []},
        description="参数分类，包含header、path、query三个数组",
    )
    requestBody: Optional[RequestBody] = Field(
        default=None,
        description="请求体信息，无请求体时为null",
    )
    responses: List[Response] = Field(
        default_factory=list,
        description="响应信息列表",
    )

    @field_validator("method")
    @classmethod
    def validate_method(cls, v):
        allowed_methods = [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "HEAD",
            "OPTIONS",
        ]
        if v.upper() not in allowed_methods:
            raise ValueError(f"Method must be one of {allowed_methods}")
        return v.upper()

    @field_validator("path")
    @classmethod
    def validate_path(cls, v):
        if not v.startswith("/"):
            raise ValueError("API path must start with /")
        return v
