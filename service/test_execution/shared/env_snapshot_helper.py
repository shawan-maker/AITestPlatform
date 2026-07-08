"""测试执行模块 - shared/env_snapshot_helper

env snapshot helper
"""
from service.test_environment.variable.snapshot_service import SnapshotService
from service.test_environment.models import TestEnvironmentSnapshot


async def create_env_snapshot(environment_id: int, *, created_by_id: int | None = None) -> TestEnvironmentSnapshot:
    return await SnapshotService.create_for_run(environment_id, created_by_id=created_by_id)
