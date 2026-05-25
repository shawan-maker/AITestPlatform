from tortoise.expressions import Q

from service.core.exceptions import AppException
from service.core.redis import is_token_revoked, revoke_token, is_user_token_invalidated
from service.core.security import (
    assert_token_type,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_remaining_seconds,
    hash_password,
    verify_password,
)
from service.user.models import User
from service.user.schemas import (
    RefreshTokenRequest,
    TokenData,
    UserBrief,
    UserRegisterRequest,
    VerifyTokenData,
)


class AuthService:
    @staticmethod
    def _to_user_brief(user: User) -> UserBrief:
        return UserBrief.model_validate(user)

    @classmethod
    async def register(cls, data: UserRegisterRequest) -> UserBrief:
        if await User.filter(username=data.username).exists():
            raise AppException("用户名已存在", 409)
        if await User.filter(email=data.email).exists():
            raise AppException("邮箱已注册", 409)
        if data.password != data.verify_password:
            raise AppException("密码不一致", 400)

        user = await User.create(
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
            is_super_admin=False,
            is_active=True,
        )
        return cls._to_user_brief(user)

    @classmethod
    async def login(cls, username: str, password: str) -> TokenData:
        user = await User.filter(
            Q(username=username) | Q(email=username)
        ).first()
        if user is None or not verify_password(password, user.password_hash):
            raise AppException("用户名或密码错误", 401)
        if user.is_deleted:
            raise AppException("账号已删除", 403)
        if not user.is_active:
            raise AppException("账号已禁用", 403)

        access_token, _, access_expires = create_access_token(user.id, user.username)
        refresh_token, _, _ = create_refresh_token(user.id)
        return TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=access_expires,
        )

    @classmethod
    async def verify(cls, user: User) -> VerifyTokenData:
        return VerifyTokenData(valid=True, user=cls._to_user_brief(user))

    @classmethod
    async def refresh(cls, data: RefreshTokenRequest) -> TokenData:
        payload = decode_token(data.refresh_token)
        assert_token_type(payload, "refresh")

        jti = payload.get("jti")
        if not jti or await is_token_revoked(jti):
            raise AppException("Token 已失效", 401)

        user = await User.get_or_none(id=int(payload["sub"]))
        if user is None:
            raise AppException("用户不存在", 401)
        if await is_user_token_invalidated(user.id, payload.get("iat")):
            raise AppException("Token 已失效", 401)
        if user.is_deleted:
            raise AppException("账号已删除", 403)
        if not user.is_active:
            raise AppException("账号已禁用", 403)

        access_token, _, access_expires = create_access_token(user.id, user.username)
        return TokenData(
            access_token=access_token,
            refresh_token=data.refresh_token,
            token_type="bearer",
            expires_in=access_expires,
        )

    @classmethod
    async def logout(
        cls,
        access_payload: dict,
        refresh_token: str | None = None,
    ) -> None:
        access_jti = access_payload.get("jti")
        if access_jti:
            ttl = get_token_remaining_seconds(access_payload)
            await revoke_token(access_jti, ttl)

        if refresh_token:
            refresh_payload = decode_token(refresh_token)
            assert_token_type(refresh_payload, "refresh")
            refresh_jti = refresh_payload.get("jti")
            if refresh_jti:
                ttl = get_token_remaining_seconds(refresh_payload)
                await revoke_token(refresh_jti, ttl)
