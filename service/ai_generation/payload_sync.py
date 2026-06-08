"""Sync LangGraph tool results to ai_generation_session.output_payload."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from service.ai_generation.models import AIGenerationSession
from service.core.enums import SessionStatus


def session_id_from_config(config: dict[str, Any] | None) -> int | None:
    if not config:
        return None
    configurable = config.get("configurable") if isinstance(config, dict) else None
    if not configurable:
        return None
    raw = configurable.get("ai_session_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


async def sync_functional_payload(session_id: int, workflow_result: dict[str, Any]) -> None:
    session = await AIGenerationSession.get_or_none(id=session_id)
    if session is None:
        return
    points = workflow_result.get("points") or workflow_result.get("test_points") or []
    cases = workflow_result.get("test_cases") or workflow_result.get("cases") or []

    # 将测试点信息注入到对应的测试用例中（按索引一一对应）
    if points and cases:
        for i, case in enumerate(cases):
            if i < len(points):
                case["test_point"] = points[i]

    session.output_payload = {"test_points": points, "cases": cases}
    session.status = SessionStatus.success
    session.error_message = None
    session.finished_at = datetime.now(timezone.utc)
    await session.save(
        update_fields=["output_payload", "status", "error_message", "finished_at"]
    )


async def sync_api_base_payload(
    session_id: int,
    *,
    base_cases: list,
    api_doc: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    session = await AIGenerationSession.get_or_none(id=session_id)
    if session is None:
        return
    payload = dict(session.output_payload or {})
    payload["base_cases"] = base_cases
    if api_doc is not None:
        payload["api_doc"] = api_doc
    if extra:
        payload.update(extra)
    session.output_payload = payload
    session.status = SessionStatus.success
    session.error_message = None
    session.finished_at = datetime.now(timezone.utc)
    await session.save(
        update_fields=["output_payload", "status", "error_message", "finished_at"]
    )
