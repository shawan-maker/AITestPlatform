"""项目管理模块 - schemas

请求/响应 Schema 定义
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from service.core.pagination import Paginated


class ProjectCreateRequest(BaseModel):
    """项目创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: str | None = Field(default=None, max_length=1024, description="项目描述，可为空")

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("项目名称不能为空")
        return stripped


class ProjectUpdateRequest(BaseModel):
    """项目更新请求"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1024)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("项目名称不能为空")
        return stripped

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.name is None and self.description is None:
            raise ValueError("至少提供 name 或 description 之一")
        return self


class ProjectListQuery(BaseModel):
    """项目列表查询query"""
    name: str | None = None
    user_id: int | None = None
    username: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ProjectMemberAddRequest(BaseModel):
    """项目成员添加请求"""
    user_id: int = Field(..., ge=1)
    role: Literal[0, 1] = Field(..., description="0=viewer, 1=editor")


class ProjectMemberUpdateRequest(BaseModel):
    """项目成员更新请求"""
    role: Literal[0, 1, 2] = Field(..., description="0=viewer, 1=editor, 2=admin(SA only)")


class ProjectOwnerTransferRequest(BaseModel):
    """项目ownertransfer请求"""
    new_owner_user_id: int = Field(..., ge=1)


class ProjectAdminSetRequest(BaseModel):
    """项目admin设置请求"""
    user_id: int = Field(..., ge=1)


class ProjectBatchDeleteRequest(BaseModel):
    """项目批量操作删除请求"""
    project_ids: list[int] = Field(..., min_length=1, max_length=50)


class ProjectBatchDeleteFailure(BaseModel):
    """项目批量操作删除failure"""
    project_id: int
    message: str
    blockers: dict[str, int] | None = None


class ProjectBatchDeleteResult(BaseModel):
    """项目批量操作删除结果"""
    deleted_ids: list[int]
    failures: list[ProjectBatchDeleteFailure]


class ProjectBrief(BaseModel):
    """项目brief"""
    id: int
    name: str
    description: str | None
    owner_id: int
    owner_username: str
    member_count: int = 0
    my_role: int | None = None
    my_role_label: str | None = None
    is_member: bool
    created_at: datetime
    updated_at: datetime


class PaginatedProjects(BaseModel):
    """paginatedprojects"""
    total: int
    page: int
    page_size: int
    items: list[ProjectBrief]


class ProjectMemberOut(BaseModel):
    """项目成员out"""
    user_id: int
    username: str
    email: str
    role: int
    role_label: str
    is_super_admin: bool = False
    joined_at: datetime


class ProjectDetail(ProjectBrief):
    """项目detail"""
    members: list[ProjectMemberOut] | None = None


class ProjectDeleteBlockers(BaseModel):
    """项目删除blockers"""
    blockers: dict[str, int]


class ProjectModuleCreateRequest(BaseModel):
    """项目模块创建请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1024)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("模块名称不能为空")
        return stripped


class ProjectModuleUpdateRequest(BaseModel):
    """项目模块更新请求"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1024)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("模块名称不能为空")
        return stripped

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.name is None and self.description is None:
            raise ValueError("至少提供 name 或 description 之一")
        return self


class ProjectModuleBrief(BaseModel):
    """项目模块brief"""
    id: int
    project_id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


PaginatedProjectModules = Paginated[ProjectModuleBrief]
