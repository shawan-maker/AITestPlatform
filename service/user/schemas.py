from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRegisterRequest(BaseModel):
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
    refresh_token: str = Field(..., min_length=1, description="Refresh Token")


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, description="可选，一并撤销 Refresh Token")


class TokenData(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class UserBrief(BaseModel):
    id: int
    username: str
    email: str
    is_super_admin: bool
    is_active: bool
    is_deleted: bool = False

    model_config = {"from_attributes": True}


class VerifyTokenData(BaseModel):
    valid: bool = True
    user: UserBrief


class UserCreateByAdminRequest(BaseModel):
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
    is_active: bool


class UserListQuery(BaseModel):
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
    project_id: int
    project_name: str
    role: int
    role_label: str


class UserDetail(BaseModel):
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
    total: int
    page: int
    page_size: int
    items: list[UserBrief]


class UserLookupBrief(BaseModel):
    id: int
    username: str
    email: str


class PaginatedUserLookup(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UserLookupBrief]


class ChangeOwnPasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=18)
    new_password: str = Field(..., min_length=6, max_length=18)
    verify_password: str = Field(..., min_length=6, max_length=18)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.verify_password:
            raise ValueError("两次密码不一致")
        return self


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=18)
    verify_password: str = Field(..., min_length=6, max_length=18)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.verify_password:
            raise ValueError("两次密码不一致")
        return self


class UserBatchDeleteRequest(BaseModel):
    user_ids: list[int] = Field(..., min_length=1, max_length=50)


class UserBatchDeleteFailure(BaseModel):
    user_id: int
    message: str


class UserBatchDeleteResult(BaseModel):
    deleted_ids: list[int]
    failures: list[UserBatchDeleteFailure]
