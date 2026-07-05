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
    import logging
    _logger = logging.getLogger(__name__)

    session = await AIGenerationSession.get_or_none(id=session_id)
    if session is None:
        return
    points = workflow_result.get("points") or workflow_result.get("test_points") or []
    cases = workflow_result.get("test_cases") or workflow_result.get("cases") or []
    
    _logger.info("[payload_sync] session=%s, points原始数量: %d, cases数量: %d", session_id, len(points), len(cases))
    _logger.info("[payload_sync] points前3个: %s", str(points[:3])[:200])

    # 将测试点格式化为前端期望的格式（每个测试点是一个带有name字段的对象）
    formatted_points = []
    for i, p in enumerate(points):
        if isinstance(p, dict):
            # p 是 {"type":"功能测试","dimension":"正向验证","test_point":"具体测试点描述"}
            point_name = p.get("test_point", str(p))
            formatted_points.append({
                "name": point_name,  # 前端使用 tp.name 显示
                "type": p.get("type", ""),
                "dimension": p.get("dimension", ""),
                "case_count": 0  # 稍后计算
            })
        else:
            formatted_points.append({"name": str(p), "case_count": 0})

    _logger.info("[payload_sync] formatted_points前3个: %s", str(formatted_points[:3])[:200])

    # 将测试点信息注入到对应的测试用例中（按索引一一对应）
    if formatted_points and cases:
        for i, case in enumerate(cases):
            if i < len(formatted_points):
                case["test_point"] = formatted_points[i]["name"]

    # 计算每个测试点的用例数
    for p in formatted_points:
        p["case_count"] = sum(1 for c in cases if c.get("test_point") == p["name"])

    _logger.info("[payload_sync] 最终test_points: %s", str(formatted_points)[:200])
    _logger.info("[payload_sync] 最终cases数量: %d", len(cases))

    session.output_payload = {"test_points": formatted_points, "cases": cases}
    if formatted_points or cases:
        session.status = SessionStatus.success
        session.error_message = None
    else:
        session.status = SessionStatus.failed
        session.error_message = "AI 未生成任何测试用例，请检查输入内容或稍后重试"
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
    if base_cases:
        session.status = SessionStatus.success
        session.error_message = None
    else:
        session.status = SessionStatus.failed
        session.error_message = "AI 未生成任何基础用例，请检查输入内容或稍后重试"
    session.finished_at = datetime.now(timezone.utc)
    await session.save(
        update_fields=["output_payload", "status", "error_message", "finished_at"]
    )
