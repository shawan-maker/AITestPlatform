"""用户管理模块 - schemas

请求/响应 Schema 定义
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=18, description="密码，6-18 位")
    verify_password: str = Field(..., min_length=6, max_length=18, description="确认密码，6-18 位")

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.verify_password:
            raise ValueError("两次密码不一致")
        return self


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., min_length=1, description="Refresh Token")


class LogoutRequest(BaseModel):
    """登出请求"""
    refresh_token: str | None = Field(default=None, description="可选，一并撤销 Refresh Token")


class TokenData(BaseModel):
    """令牌data"""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class UserBrief(BaseModel):
    """用户brief"""
    id: int
    username: str
    email: str
    is_super_admin: bool
    is_active: bool
    is_deleted: bool = False

    model_config = {"from_attributes": True}


class VerifyTokenData(BaseModel):
    """验证令牌data"""
    valid: bool = True
    user: UserBrief


class UserCreateByAdminRequest(BaseModel):
    """用户创建byadmin请求"""
    username: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=18)
    verify_password: str = Field(..., min_length=6, max_length=18)
    is_active: bool = True
    is_super_admin: bool = False

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.verify_password:
            raise ValueError("两次密码不一致")
        return self


class UserStatusUpdateRequest(BaseModel):
    """用户状态更新请求"""
    is_active: bool


class UserListQuery(BaseModel):
    """用户列表查询query"""
    username: str | None = None
    email: str | None = None
    project_name: str | None = None
    project_id: int | None = None
    is_active: bool | None = None
    is_super_admin: bool | None = None
    is_deleted: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class UserProjectMembership(BaseModel):
    """用户项目membership"""
    project_id: int
    project_name: str
    role: int
    role_label: str


class UserDetail(BaseModel):
    """用户detail"""
    id: int
    username: str
    email: str
    is_super_admin: bool
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    projects: list[UserProjectMembership] = Field(default_factory=list)


class PaginatedUsers(BaseModel):
    """paginatedusers"""
    total: int
    page: int
    page_size: int
    items: list[UserBrief]


class UserLookupBrief(BaseModel):
    """用户lookupbrief"""
    id: int
    username: str
    email: str


class PaginatedUserLookup(BaseModel):
    """paginated用户lookup"""
    total: int
    page: int
    page_size: int
    items: list[UserLookupBrief]


class ChangeOwnPasswordRequest(BaseModel):
    """changeown密码请求"""
    old_password: str = Field(..., min_length=6, max_length=18)
    new_password: str = Field(..., min_length=6, max_length=18)
    verify_password: str = Field(..., min_length=6, max_length=18)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.verify_password:
            raise ValueError("两次密码不一致")
        return self


class AdminResetPasswordRequest(BaseModel):
    """admin重置密码请求"""
    new_password: str = Field(..., min_length=6, max_length=18)
    verify_password: str = Field(..., min_length=6, max_length=18)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.verify_password:
            raise ValueError("两次密码不一致")
        return self


class UserBatchDeleteRequest(BaseModel):
    """用户批量操作删除请求"""
    user_ids: list[int] = Field(..., min_length=1, max_length=50)


class UserBatchDeleteFailure(BaseModel):
    """用户批量操作删除failure"""
    user_id: int
    message: str


class UserBatchDeleteResult(BaseModel):
    """用户批量操作删除结果"""
    deleted_ids: list[int]
    failures: list[UserBatchDeleteFailure]
