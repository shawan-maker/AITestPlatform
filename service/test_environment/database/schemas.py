"""测试环境管理模块 - database/schemas

请求/响应 Schema 定义
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from service.core.enums import DbType
from service.core.pagination import Paginated


class DbConnectionConfigInput(BaseModel):
    """dbconnection配置input"""
    host: str
    port: int = 3306
    username: str
    password: str | None = None
    database_name: str | None = None


class DbConnectionCreateRequest(BaseModel):
    """dbconnection创建请求"""
    connection_name: str = Field(..., min_length=1, max_length=50)
    server_name: str = Field(..., min_length=1, max_length=50)
    db_type: DbType
    config: DbConnectionConfigInput
    description: str | None = Field(default=None, max_length=255)
    environment_ids: list[int] = Field(default_factory=list)


class DbConnectionUpdateRequest(BaseModel):
    """dbconnection更新请求"""
    connection_name: str | None = Field(default=None, min_length=1, max_length=50)
    server_name: str | None = Field(default=None, min_length=1, max_length=50)
    db_type: DbType | None = None
    config: DbConnectionConfigInput | None = None
    description: str | None = Field(default=None, max_length=255)
    environment_ids: list[int] | None = None

    @model_validator(mode="after")
    def at_least_one(self):
        if all(
            v is None
            for v in (
                self.connection_name,
                self.server_name,
                self.db_type,
                self.config,
                self.description,
                self.environment_ids,
            )
        ):
            raise ValueError("至少提供一个可更新字段")
        return self


class DbConnectionBrief(BaseModel):
    """dbconnectionbrief"""
    id: int
    connection_name: str
    server_name: str
    db_type: DbType
    description: str | None
    host: str | None = None
    username: str | None = None
    project_id: int | None
    created_by_id: int | None
    is_bound: bool
    created_at: datetime
    updated_at: datetime


class DbConnectionDetail(DbConnectionBrief):
    """dbconnectiondetail"""
    config: dict[str, Any]
    environment_ids: list[int] = Field(default_factory=list)


class DbConnectionTestResult(BaseModel):
    """dbconnection测试结果"""
    success: bool
    message: str | None
    tested_at: datetime


class DbConnectionTestLogOut(BaseModel):
    """dbconnection测试logout"""
    id: int
    success: bool
    message: str | None
    tested_by_id: int | None
    tested_at: datetime


PaginatedDbConnections = Paginated[DbConnectionBrief]
PaginatedDbTestLogs = Paginated[DbConnectionTestLogOut]


class EnvironmentDbBindRequest(BaseModel):
    """环境dbbind请求"""
    db_connection_ids: list[int]


class ExportDbConnectionEmbed(BaseModel):
    """导出dbconnectionembed"""
    connection_name: str
    server_name: str
    db_type: DbType
    config: DbConnectionConfigInput
    description: str | None = None


class DbConnectionBatchDeleteRequest(BaseModel):
    """dbconnection批量操作删除请求"""
    connection_ids: list[int] = Field(..., min_length=1, max_length=50)


class DbConnectionBatchDeleteFailure(BaseModel):
    """dbconnection批量操作删除failure"""
    connection_id: int
    message: str


class DbConnectionBatchDeleteResult(BaseModel):
    """dbconnection批量操作删除结果"""
    deleted_ids: list[int]
    failures: list[DbConnectionBatchDeleteFailure]
