"""接口测试模块 - debug/schemas

请求/响应 Schema 定义
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DebugTemplateOut(BaseModel):
    """调试templateout"""
    interface_id: int
    payload: dict[str, Any] | None
    default_file_id: int | None
    updated_at: datetime | None


class DebugTemplateSaveRequest(BaseModel):
    """调试template保存请求"""
    payload: dict[str, Any] | None = None
    default_file_id: int | None = Field(default=None, ge=1)


class DebugRunRequest(BaseModel):
    """调试执行请求"""
    environment_id: int = Field(..., ge=1)
    payload: dict[str, Any] | None = None
    file_id: int | None = Field(default=None, ge=1)
    # v2-L2: 调试取消令牌标识（前端传入，后端用于标记cancelled状态）
    cancel_token: str | None = None


class DebugRunOut(BaseModel):
    """调试执行out"""
    run_record_id: int
    status: str
    duration_ms: int | None
