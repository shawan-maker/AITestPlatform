"""用户管理模块 - bootstrap

bootstrap
"""
import logging

from service.core.security import hash_password
from service.user.models import User

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@test.com"
DEFAULT_ADMIN_PASSWORD = "123456"


async def ensure_default_super_admin() -> None:
    """首次启动时创建默认超级管理员；已存在则跳过。"""
    if await User.filter(username=DEFAULT_ADMIN_USERNAME).exists():
        return

    await User.create(
        username=DEFAULT_ADMIN_USERNAME,
        email=DEFAULT_ADMIN_EMAIL,
        password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        is_super_admin=True,
        is_active=True,
        is_deleted=False,
    )
    logger.info(
        "已创建默认超级管理员：username=%s, email=%s（请尽快修改默认密码）",
        DEFAULT_ADMIN_USERNAME,
        DEFAULT_ADMIN_EMAIL,
    )
