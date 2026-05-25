from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from service.core.config import REDIS_URL

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None
_redis_checked = False


def _revoked_key(jti: str) -> str:
    return f"auth:revoked:{jti}"


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
    await client.setex(_revoked_key(jti), ttl_seconds, "1")


async def close_redis() -> None:
    global _redis_client, _redis_checked
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
    _redis_checked = False
