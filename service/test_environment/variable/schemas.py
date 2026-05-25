import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from service.core.enums import ConfigType, DebugVarSource
from service.core.pagination import Paginated
from service.test_environment.database.schemas import (
    DbConnectionConfigInput,
    ExportDbConnectionEmbed,
)
from service.test_environment.function.schemas import ExportFunctionEmbed, FunctionBindItem

CONFIG_GROUPS = Literal["base", "headers", "envs"]


class CatalogCreateRequest(BaseModel):
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
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = None

    @model_validator(mode="after")
    def at_least_one(self):
        if self.name is None and self.parent_id is None:
            raise ValueError("至少提供 name 或 parent_id 之一")
        return self


class CatalogTreeNode(BaseModel):
    id: int
    name: str
    level: int
    parent_id: int | None
    environment_count: int = 0
    children: list["CatalogTreeNode"] = Field(default_factory=list)


class CatalogOut(BaseModel):
    id: int
    project_id: int
    parent_id: int | None
    name: str
    level: int
    created_at: datetime
    updated_at: datetime


class EnvironmentCreateRequest(BaseModel):
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
    env_name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    catalog_id: int | None = None

    @model_validator(mode="after")
    def at_least_one(self):
        if self.env_name is None and self.description is None and self.catalog_id is None:
            raise ValueError("至少提供一个可更新字段")
        return self


class EnvironmentBrief(BaseModel):
    id: int
    project_id: int
    catalog_id: int | None
    env_name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class EnvironmentDetail(EnvironmentBrief):
    db_connection_ids: list[int] = Field(default_factory=list)
    function_file_ids: list[int] = Field(default_factory=list)
    active_snapshot_id: int | None = None


PaginatedEnvironments = Paginated[EnvironmentBrief]


class ConfigItemCreateRequest(BaseModel):
    config_group: CONFIG_GROUPS
    name: str = Field(..., min_length=1, max_length=100)
    config_type: ConfigType = ConfigType.scalar
    value: str | None = None
    remark: str | None = Field(default=None, max_length=255)


class ConfigItemUpdateRequest(BaseModel):
    config_type: ConfigType | None = None
    value: str | None = None
    remark: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def at_least_one(self):
        if self.config_type is None and self.value is None and self.remark is None:
            raise ValueError("至少提供一个可更新字段")
        return self


class ConfigGroupItem(BaseModel):
    name: str
    config_type: ConfigType = ConfigType.scalar
    value: str | None = None
    remark: str | None = None


class ConfigGroupReplaceRequest(BaseModel):
    items: list[ConfigGroupItem]


class ConfigItemOut(BaseModel):
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
    set_active: bool = True


class SnapshotBrief(BaseModel):
    id: int
    environment_id: int
    version: int
    is_active: bool
    payload_summary: dict | None
    created_by_id: int | None
    created_at: datetime


class SnapshotDetail(SnapshotBrief):
    payload: dict


ImportMode = Literal["reference", "embed"]


class EnvironmentExportBundle(BaseModel):
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
    bundle: EnvironmentExportBundle
    overwrite: bool = False
    import_mode: ImportMode | None = None


class DebugVarItem(BaseModel):
    var_key: str = Field(..., min_length=1, max_length=100)
    var_value: str | None = None
    source: DebugVarSource = DebugVarSource.manual


class DebugVarBatchUpsertRequest(BaseModel):
    items: list[DebugVarItem]


class DebugVarSyncItem(BaseModel):
    var_key: str = Field(..., min_length=1, max_length=100)
    var_value: str | None = None


class DebugVarSyncRequest(BaseModel):
    items: list[DebugVarSyncItem]


class DebugVarOut(BaseModel):
    id: int
    environment_id: int
    var_key: str
    var_value: str | None
    source: DebugVarSource
    updated_by_id: int | None
    updated_at: datetime


CatalogTreeNode.model_rebuild()
