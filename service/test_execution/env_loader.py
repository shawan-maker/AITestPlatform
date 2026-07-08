"""测试执行模块 - env_loader

加载器
"""
from typing import Any

from service.core.async_utils import run_on_main_loop
from service.test_environment.file.resolver import FileResolver
from service.test_environment.variable.assembler import TestEnvDataAssembler


async def load_test_env_data(
    environment_id: int,
    *,
    use_snapshot: bool = False,
) -> dict:
    return await TestEnvDataAssembler.get_test_env_data(
        environment_id,
        use_snapshot=use_snapshot,
    )


def load_test_env_data_plain(
    environment_id: int,
    *,
    use_snapshot: bool = False,
) -> dict:
    """同步包装器 —— 在后台线程中安全查询测试环境数据。

    通过 run_on_main_loop 将 DB 查询调度到主事件循环，
    复用已有的 Tortoise ORM 连接池，不重新初始化/关闭连接。
    独立脚本环境下（无主循环）自动降级为 asyncio.run()。
    """
    return run_on_main_loop(
        TestEnvDataAssembler.get_test_env_data(
            environment_id,
            use_snapshot=use_snapshot,
        )
    )


async def resolve_case_files(project_id: int, case_payload: dict[str, Any]) -> dict[str, Any]:
    return await FileResolver.resolve_request_files(project_id, case_payload)
