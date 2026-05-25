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

    model_config = {"from_attributes": True}


class VerifyTokenData(BaseModel):
    valid: bool = True
    user: UserBrief
