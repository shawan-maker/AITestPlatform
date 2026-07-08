"""测试环境管理模块 - variable/schemas

请求/响应 Schema 定义
"""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from service.core.enums import ConfigType
from service.core.pagination import Paginated
from service.test_environment.database.schemas import (
    DbConnectionConfigInput,
    ExportDbConnectionEmbed,
)
from service.test_environment.function.schemas import ExportFunctionEmbed, FunctionBindItem

CONFIG_GROUPS = Literal["base", "headers", "envs"]


class CatalogCreateRequest(BaseModel):
    """目录创建请求"""
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("目录名称不能为空")
        return stripped


class CatalogUpdateRequest(BaseModel):
    """目录更新请求"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = None

    @model_validator(mode="after")
    def at_least_one(self):
        if self.name is None and self.parent_id is None:
            raise ValueError("至少提供 name 或 parent_id 之一")
        return self


class CatalogTreeNode(BaseModel):
    """目录treenode"""
    id: int
    name: str
    level: int
    parent_id: int | None
    environment_count: int = 0
    children: list["CatalogTreeNode"] = Field(default_factory=list)


class CatalogOut(BaseModel):
    """目录out"""
    id: int
    project_id: int
    parent_id: int | None
    name: str
    level: int
    created_at: datetime
    updated_at: datetime


class EnvironmentCreateRequest(BaseModel):
    """环境创建请求"""
    env_name: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    catalog_id: int | None = None

    @field_validator("env_name")
    @classmethod
    def strip_env_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("变量文件名称不能为空")
        return stripped


class EnvironmentUpdateRequest(BaseModel):
    """环境更新请求"""
    env_name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    catalog_id: int | None = None

    @model_validator(mode="after")
    def at_least_one(self):
        if self.env_name is None and self.description is None and self.catalog_id is None:
            raise ValueError("至少提供一个可更新字段")
        return self


class EnvironmentBrief(BaseModel):
    """环境brief"""
    id: int
    project_id: int
    catalog_id: int | None
    env_name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class EnvironmentDetail(EnvironmentBrief):
    """环境detail"""
    db_connection_ids: list[int] = Field(default_factory=list)
    function_file_ids: list[int] = Field(default_factory=list)
    function_bindings: list[FunctionBindItem] = Field(default_factory=list)


PaginatedEnvironments = Paginated[EnvironmentBrief]


class ConfigItemCreateRequest(BaseModel):
    """配置item创建请求"""
    config_group: CONFIG_GROUPS
    name: str = Field(..., min_length=1, max_length=100)
    config_type: ConfigType = ConfigType.scalar
    value: str | None = None
    remark: str | None = Field(default=None, max_length=255)


class ConfigItemUpdateRequest(BaseModel):
    """配置item更新请求"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    config_type: ConfigType | None = None
    value: str | None = None
    remark: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def at_least_one(self):
        if self.name is None and self.config_type is None and self.value is None and self.remark is None:
            raise ValueError("至少提供一个可更新字段")
        return self


class ConfigGroupItem(BaseModel):
    """配置groupitem"""
    name: str
    config_type: ConfigType = ConfigType.scalar
    value: str | None = None
    remark: str | None = None


class ConfigGroupReplaceRequest(BaseModel):
    """配置groupreplace请求"""
    items: list[ConfigGroupItem]


class ConfigItemOut(BaseModel):
    """配置itemout"""
    id: int
    environment_id: int
    config_group: str
    name: str
    config_type: ConfigType
    value: str | None
    remark: str | None
    created_at: datetime
    updated_at: datetime


class SnapshotCreateRequest(BaseModel):
    """快照创建请求"""
    set_active: bool = True


class SnapshotBrief(BaseModel):
    """快照brief"""
    id: int
    environment_id: int
    version: int
    is_active: bool
    payload_summary: dict | None
    created_by_id: int | None
    created_at: datetime


class SnapshotDetail(SnapshotBrief):
    """快照detail"""
    payload: dict


ImportMode = Literal["reference", "embed"]


class EnvironmentExportBundle(BaseModel):
    """环境导出bundle"""
    env_name: str
    description: str | None
    catalog_id: int | None
    import_mode: ImportMode = "embed"
    configs: list[ConfigItemOut] = Field(default_factory=list)
    db_connection_ids: list[int] = Field(default_factory=list)
    db_connections: list[ExportDbConnectionEmbed] = Field(default_factory=list)
    function_bindings: list[FunctionBindItem] = Field(default_factory=list)
    functions: list[ExportFunctionEmbed] = Field(default_factory=list)


class EnvironmentImportRequest(BaseModel):
    """环境import请求"""
    bundle: EnvironmentExportBundle
    overwrite: bool = False
    import_mode: ImportMode | None = None


CatalogTreeNode.model_rebuild()
