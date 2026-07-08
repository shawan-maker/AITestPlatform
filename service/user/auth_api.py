"""用户管理模块 - auth_api

API 路由端点
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from service.core.deps import get_access_payload, get_current_active_user
from service.core.response import success
from service.user.models import User
from service.user.schemas import LogoutRequest, RefreshTokenRequest, UserRegisterRequest
from service.user.service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", summary="用户注册")
async def register(data: UserRegisterRequest):
    user = await AuthService.register(data)
    return success(data=user, message="注册成功")


@router.post(
    "/login",
    summary="用户登录（OAuth2）",
    description="使用 OAuth2 表单登录，username 字段支持用户名或邮箱。"
    " Swagger Authorize 需手动粘贴 access_token。",
)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    token_data = await AuthService.login(form.username, form.password)
    return {
        "access_token": token_data.access_token,
        "token_type": token_data.token_type,
        "code": 200,
        "message": "登录成功",
        "data": token_data.model_dump(),
    }


@router.post("/logout", summary="用户登出")
async def logout(
    body: LogoutRequest | None = None,
    payload: dict = Depends(get_access_payload),
):
    refresh_token = body.refresh_token if body else None
    await AuthService.logout(payload, refresh_token)
    return success(message="已登出")


@router.get("/verify", summary="Token 校验")
async def verify_token(user: User = Depends(get_current_active_user)):
    data = await AuthService.verify(user)
    return success(data=data)


@router.post("/refresh", summary="Token 刷新")
async def refresh_token(data: RefreshTokenRequest):
    token_data = await AuthService.refresh(data)
    return success(data=token_data)
