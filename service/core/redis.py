from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from service.core.config import REDIS_URL, REFRESH_TOKEN_EXPIRE_DAYS

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None
_redis_checked = False


def _revoked_key(jti: str) -> str:
    return f"auth:revoked:{jti}"


def _user_invalid_before_key(user_id: int) -> str:
    return f"auth:user:{user_id}:invalid_before"


def _user_invalidation_ttl() -> int:
    return REFRESH_TOKEN_EXPIRE_DAYS * 86400


def _normalize_timestamp(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    return None


async def get_redis() -> Redis | None:
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    if not REDIS_URL:
        logger.info("REDIS_URL 未配置，Token 黑名单功能不可用")
        return None
    try:
        from redis.asyncio import Redis

        _redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
        await _redis_client.ping()
    except Exception as exc:
        logger.warning("Redis 连接失败，Token 黑名单功能不可用: %s", exc)
        _redis_client = None
    return _redis_client


async def is_token_revoked(jti: str) -> bool:
    client = await get_redis()
    if client is None:
        return False
    return bool(await client.exists(_revoked_key(jti)))


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    client = await get_redis()
    if client is None:
        return
    await client.setex(_revoked_key(jti), max(ttl_seconds, 1), "1")


async def invalidate_user_tokens(user_id: int) -> None:
    client = await get_redis()
    if client is None:
        return
    now = int(time.time())
    await client.setex(
        _user_invalid_before_key(user_id),
        _user_invalidation_ttl(),
        str(now),
    )


async def is_user_token_invalidated(user_id: int, token_iat: Any) -> bool:
    client = await get_redis()
    if client is None:
        return False
    invalid_before = await client.get(_user_invalid_before_key(user_id))
    if not invalid_before:
        return False
    token_ts = _normalize_timestamp(token_iat)
    if token_ts is None:
        return False
    return token_ts < float(invalid_before)


async def close_redis() -> None:
    global _redis_client, _redis_checked
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
    _redis_checked = False
