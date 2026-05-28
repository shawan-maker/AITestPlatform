"""Phase 2 agent session + SSE tests."""

import pytest

from service.ai_generation.api_agent_service import ApiAgentService
from service.ai_generation.functional_agent_service import FunctionalAgentService
from service.ai_generation.meta import get_agent_meta
from service.ai_generation.models import AIGenerationMessage, AIGenerationSession
from service.ai_generation.schemas import (
    ApiConfirmRequest,
    ApiCreateSessionRequest,
    FunctionalCreateSessionRequest,
    FunctionalSaveRequest,
)
from service.ai_generation.session_schemas import AgentMessageRequest
from service.core.enums import SessionStatus, SourceChannel


def test_agent_meta_history_limit():
    meta = get_agent_meta()
    assert meta.history_limit >= 1


@pytest.mark.asyncio
async def test_functional_create_session_and_mock_message(agent_context):
    session = await FunctionalAgentService.create_session(
        agent_context["viewer"],
        FunctionalCreateSessionRequest(
            project_id=agent_context["project_id"],
            requirement_text="用户登录与权限校验",
            title="登录用例",
        ),
    )
    assert session.id
    assert session.source_channel == SourceChannel.agent_center
    assert session.title == "登录用例"

    chunks: list[str] = []
    async for chunk in FunctionalAgentService.stream_message(
        agent_context["viewer"],
        session.id,
        AgentMessageRequest(content="请生成功能用例"),
    ):
        chunks.append(chunk)

    assert any("event: done" in c for c in chunks)
    refreshed = await FunctionalAgentService.get_session(agent_context["viewer"], session.id)
    assert refreshed.status == SessionStatus.success
    assert refreshed.output_payload.get("cases")

    messages = await FunctionalAgentService.list_messages(
        agent_context["viewer"], session.id
    )
    assert any(m.role.value == "user" for m in messages)
    assert any(m.role.value == "assistant" for m in messages)


@pytest.mark.asyncio
async def test_functional_multi_turn_same_session(agent_context):
    session = await FunctionalAgentService.create_session(
        agent_context["viewer"],
        FunctionalCreateSessionRequest(
            project_id=agent_context["project_id"],
            requirement_text="订单支付流程",
        ),
    )
    async for _ in FunctionalAgentService.stream_message(
        agent_context["viewer"],
        session.id,
        AgentMessageRequest(content="第一轮生成"),
    ):
        pass
    async for _ in FunctionalAgentService.stream_message(
        agent_context["viewer"],
        session.id,
        AgentMessageRequest(content="增加边界值用例"),
    ):
        pass
    second = await FunctionalAgentService.get_session(agent_context["viewer"], session.id)
    assert second.output_payload.get("cases")
    assert second.status == SessionStatus.success
    msg_count = await AIGenerationMessage.filter(session_id=session.id).count()
    assert msg_count >= 4


@pytest.mark.asyncio
async def test_functional_session_fifo(agent_context, monkeypatch):
    monkeypatch.setenv("AI_AGENT_SESSION_HISTORY_LIMIT", "2")
    from importlib import reload
    import service.core.config as cfg

    reload(cfg)

    for i in range(3):
        await FunctionalAgentService.create_session(
            agent_context["viewer"],
            FunctionalCreateSessionRequest(
                project_id=agent_context["project_id"],
                requirement_text=f"需求-{i}",
            ),
        )

    listed = await FunctionalAgentService.list_sessions(
        agent_context["viewer"], agent_context["project_id"]
    )
    assert len(listed) <= 2


@pytest.mark.asyncio
async def test_functional_editor_save_after_agent(agent_context):
    session = await FunctionalAgentService.create_session(
        agent_context["viewer"],
        FunctionalCreateSessionRequest(
            project_id=agent_context["project_id"],
            requirement_text="保存测试",
        ),
    )
    async for _ in FunctionalAgentService.stream_message(
        agent_context["viewer"],
        session.id,
        AgentMessageRequest(content="生成用例"),
    ):
        pass
    save_result = await FunctionalAgentService.save(
        agent_context["editor"],
        session.id,
        FunctionalSaveRequest(
            catalog_id=agent_context["func_catalog_id"],
            case_indexes=[0],
        ),
    )
    assert save_result.created_case_ids


@pytest.mark.asyncio
async def test_api_agent_session_mock_and_confirm(agent_context):
    session = await ApiAgentService.create_session(
        agent_context["viewer"],
        ApiCreateSessionRequest(
            project_id=agent_context["project_id"],
            interface_id=agent_context["interface_id"],
        ),
    )
    async for _ in ApiAgentService.stream_message(
        agent_context["viewer"],
        session.id,
        AgentMessageRequest(content="生成基础用例"),
    ):
        pass
    refreshed = await ApiAgentService.get_session(agent_context["viewer"], session.id)
    assert refreshed.output_payload.get("base_cases")

    result = await ApiAgentService.confirm(
        agent_context["editor"],
        ApiConfirmRequest(
            session_id=session.id,
            selected_indexes=[0],
            environment_id=agent_context["environment_id"],
            interface_id=agent_context["interface_id"],
        ),
    )
    assert result.created_case_ids


@pytest.mark.asyncio
async def test_preview_interface_detail_source_channel(agent_context):
    from service.api_test.case.generation_service import ApiCaseGenerationService
    from service.api_test.case.schemas import GeneratePreviewRequest

    preview = await ApiCaseGenerationService.preview(
        agent_context["viewer"],
        agent_context["interface_id"],
        GeneratePreviewRequest(environment_id=agent_context["environment_id"]),
    )
    row = await AIGenerationSession.get(id=preview.session_id)
    assert row.source_channel == SourceChannel.interface_detail


@pytest.mark.asyncio
async def test_list_sessions_scoped_by_user(agent_context):
    other = await FunctionalAgentService.create_session(
        agent_context["editor"],
        FunctionalCreateSessionRequest(
            project_id=agent_context["project_id"],
            requirement_text="editor session",
        ),
    )
    viewer_list = await FunctionalAgentService.list_sessions(
        agent_context["viewer"], agent_context["project_id"]
    )
    assert all(item.id != other.id for item in viewer_list)
    editor_list = await FunctionalAgentService.list_sessions(
        agent_context["editor"], agent_context["project_id"]
    )
    assert any(item.id == other.id for item in editor_list)
