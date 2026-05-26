import asyncio
from typing import Any

from service.core.database import close_db, init_db
from service.test_environment.file.resolver import FileResolver
from service.test_environment.variable.assembler import TestEnvDataAssembler


async def load_test_env_data(
    environment_id: int,
    *,
    use_snapshot: bool = True,
    merge_debug: bool = True,
) -> dict:
    return await TestEnvDataAssembler.get_test_env_data(
        environment_id,
        use_snapshot=use_snapshot,
        merge_debug=merge_debug,
    )


def load_test_env_data_plain(
    environment_id: int,
    *,
    use_snapshot: bool = True,
    merge_debug: bool = True,
) -> dict:
    async def _load() -> dict:
        await init_db()
        try:
            return await TestEnvDataAssembler.get_test_env_data(
                environment_id,
                use_snapshot=use_snapshot,
                merge_debug=merge_debug,
            )
        finally:
            await close_db()

    return asyncio.run(_load())


async def resolve_case_files(project_id: int, case_payload: dict[str, Any]) -> dict[str, Any]:
    return await FileResolver.resolve_request_files(project_id, case_payload)
