from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from service.core.config import API_V1_PREFIX
from service.core.exceptions import AppException
from service.core.redis import is_token_revoked, is_user_token_invalidated
from service.core.security import assert_token_type, decode_token
from service.user.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_PREFIX}/auth/login")


async def get_access_payload(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    assert_token_type(payload, "access")
    jti = payload.get("jti")
    if not jti or await is_token_revoked(jti):
        raise AppException("Token 已失效", 401)
    user_id = payload.get("sub")
    if user_id and await is_user_token_invalidated(int(user_id), payload.get("iat")):
        raise AppException("Token 已失效", 401)
    return payload


async def get_current_user(payload: dict = Depends(get_access_payload)) -> User:
    user = await User.get_or_none(id=int(payload["sub"]))
    if user is None:
        raise AppException("用户不存在", 401)
    if user.is_deleted:
        raise AppException("账号已删除", 401)
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise AppException("账号已禁用", 403)
    return user


async def get_current_super_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    if not user.is_super_admin:
        raise AppException("需要超级管理员权限", 403)
    return user
