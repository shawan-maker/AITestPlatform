from service.core.exceptions import AppException
from service.test_environment.models import TestEnvironment, TestEnvironmentSnapshot
from service.test_environment.permissions import ensure_project_editor, ensure_project_viewer
from service.test_environment.variable.schemas import (
    SnapshotBrief,
    SnapshotCreateRequest,
    SnapshotDetail,
)
from service.test_environment.variable.assembler import (
    TestEnvDataAssembler,
    build_payload_summary,
)
from service.user.models import User

MAX_SNAPSHOTS = 3


class SnapshotService:
    @classmethod
    async def _get_or_404(cls, snapshot_id: int) -> TestEnvironmentSnapshot:
        snap = await TestEnvironmentSnapshot.get_or_none(id=snapshot_id)
        if snap is None:
            raise AppException("快照不存在", 404)
        return snap

    @classmethod
    async def list_snapshots(cls, user: User, environment_id: int) -> list[SnapshotBrief]:
        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise AppException("变量文件不存在", 404)
        await ensure_project_viewer(env.project_id, user)
        snaps = (
            await TestEnvironmentSnapshot.filter(environment_id=environment_id)
            .order_by("-created_at")
            .limit(MAX_SNAPSHOTS)
        )
        return [cls._to_brief(s) for s in snaps]

    @classmethod
    async def create(
        cls, user: User, environment_id: int, data: SnapshotCreateRequest
    ) -> SnapshotDetail:
        env = await TestEnvironment.get_or_none(id=environment_id)
        if env is None:
            raise AppException("变量文件不存在", 404)
        await ensure_project_editor(env.project_id, user)
        payload = await TestEnvDataAssembler.assemble(environment_id)
        summary = build_payload_summary(payload)
        latest = (
            await TestEnvironmentSnapshot.filter(environment_id=environment_id)
            .order_by("-version")
            .first()
        )
        version = (latest.version + 1) if latest else 1
        if data.set_active:
            await TestEnvironmentSnapshot.filter(environment_id=environment_id).update(
                is_active=False
            )
        snap = await TestEnvironmentSnapshot.create(
            environment_id=environment_id,
            payload=payload,
            payload_summary=summary,
            version=version,
            is_active=data.set_active,
            created_by_id=user.id,
        )
        snaps = (
            await TestEnvironmentSnapshot.filter(environment_id=environment_id)
            .order_by("created_at")
        )
        if len(snaps) > MAX_SNAPSHOTS:
            to_delete = snaps[: len(snaps) - MAX_SNAPSHOTS]
            for old in to_delete:
                await old.delete()
        return cls._to_detail(snap)

    @classmethod
    async def get_detail(cls, user: User, snapshot_id: int) -> SnapshotDetail:
        snap = await cls._get_or_404(snapshot_id)
        env = await TestEnvironment.get(id=snap.environment_id)
        await ensure_project_viewer(env.project_id, user)
        return cls._to_detail(snap)

    @classmethod
    async def activate(cls, user: User, snapshot_id: int) -> SnapshotBrief:
        snap = await cls._get_or_404(snapshot_id)
        env = await TestEnvironment.get(id=snap.environment_id)
        await ensure_project_editor(env.project_id, user)
        await TestEnvironmentSnapshot.filter(environment_id=snap.environment_id).update(
            is_active=False
        )
        snap.is_active = True
        await snap.save()
        return cls._to_brief(snap)

    @classmethod
    async def delete(cls, user: User, snapshot_id: int) -> None:
        snap = await cls._get_or_404(snapshot_id)
        env = await TestEnvironment.get(id=snap.environment_id)
        await ensure_project_editor(env.project_id, user)
        await snap.delete()

    @staticmethod
    def _to_brief(snap: TestEnvironmentSnapshot) -> SnapshotBrief:
        return SnapshotBrief(
            id=snap.id,
            environment_id=snap.environment_id,
            version=snap.version,
            is_active=snap.is_active,
            payload_summary=snap.payload_summary,
            created_by_id=snap.created_by_id,
            created_at=snap.created_at,
        )

    @staticmethod
    def _to_detail(snap: TestEnvironmentSnapshot) -> SnapshotDetail:
        brief = SnapshotService._to_brief(snap)
        payload = snap.payload
        if payload and isinstance(payload.get("db"), list):
            for item in payload["db"]:
                cfg = item.get("config") or {}
                if cfg.get("password"):
                    cfg["password"] = "***"
        return SnapshotDetail(**brief.model_dump(), payload=payload or {})
