import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from service.core.settings import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from service.core.exceptions import AppException

TokenType = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _build_token(
    *,
    user_id: int,
    token_type: TokenType,
    username: str | None = None,
    expires_delta: timedelta,
) -> tuple[str, str, int]:
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    expires_in = int(expires_delta.total_seconds())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expire,
    }
    if username is not None:
        payload["username"] = username
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, jti, expires_in


def create_access_token(user_id: int, username: str) -> tuple[str, str, int]:
    return _build_token(
        user_id=user_id,
        token_type="access",
        username=username,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> tuple[str, str, int]:
    return _build_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise AppException("Token 无效或已过期", 401) from exc
    return payload


def assert_token_type(payload: dict[str, Any], expected: TokenType) -> None:
    if payload.get("type") != expected:
        raise AppException("Token 类型不正确", 401)


def get_token_remaining_seconds(payload: dict[str, Any]) -> int:
    exp = payload.get("exp")
    if exp is None:
        return 0
    if isinstance(exp, datetime):
        expire_at = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
    else:
        expire_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    remaining = int((expire_at - datetime.now(timezone.utc)).total_seconds())
    return max(remaining, 1)
