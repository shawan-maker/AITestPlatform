from service.test_environment.models import TestEnvironmentSnapshot
from service.test_environment.variable.assembler import (
    TestEnvDataAssembler,
    build_payload_summary,
)


async def create_env_snapshot(environment_id: int, *, created_by_id: int | None = None) -> TestEnvironmentSnapshot:
    payload = await TestEnvDataAssembler.assemble(environment_id)
    summary = build_payload_summary(payload)
    latest = (
        await TestEnvironmentSnapshot.filter(environment_id=environment_id)
        .order_by("-version")
        .first()
    )
    version = (latest.version + 1) if latest else 1
    return await TestEnvironmentSnapshot.create(
        environment_id=environment_id,
        payload=payload,
        payload_summary=summary,
        version=version,
        is_active=False,
        created_by_id=created_by_id,
    )
