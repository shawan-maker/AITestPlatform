import pytest

from service.ai_generation.api import router as ai_generation_router
from service.ai_generation.api_agent_api import router as api_agent_router
from service.ai_generation.functional_agent_api import router as functional_agent_router
from service.ai_generation.functional_agent_service import FunctionalAgentService
from service.ai_generation.meta import get_agent_meta
from service.ai_generation.api_agent_service import ApiAgentService
from service.ai_generation.schemas import (
    ApiConfirmRequest,
    ApiGenerateFromDocRequest,
    ApiGenerateFromInterfaceRequest,
    FunctionalGenerateRequest,
    FunctionalSaveRequest,
)
from service.core.enums import SessionStatus
from service.core.exceptions import AppException
from tests.ai_generation.conftest import wait_for_functional_session


def test_agent_meta():
    meta = get_agent_meta()
    assert meta.single_interface_only is True
    assert len(meta.functional_prompt_templates) >= 1
    assert len(meta.api_prompt_templates) >= 1


def test_agent_routes_mounted():
    paths = {route.path for route in ai_generation_router.routes}
    assert "/ai-generation/meta" in paths
    func_paths = {route.path for route in functional_agent_router.routes}
    assert "/functional/generate" in func_paths
    assert "/functional/sessions/{session_id}/save" in func_paths
    api_paths = {route.path for route in api_agent_router.routes}
    assert "/api/generate-from-doc" in api_paths
    assert "/api/confirm" in api_paths


@pytest.mark.asyncio
async def test_functional_viewer_can_generate(agent_context):
    result = await FunctionalAgentService.generate(
        agent_context["viewer"],
        FunctionalGenerateRequest(
            project_id=agent_context["project_id"],
            requirement_text="用户登录与权限校验",
        ),
    )
    session = await wait_for_functional_session(result.id, agent_context["viewer"])
    assert session.status == SessionStatus.success
    assert session.output_payload is not None


@pytest.mark.asyncio
async def test_functional_viewer_cannot_save(agent_context):
    result = await FunctionalAgentService.generate(
        agent_context["viewer"],
        FunctionalGenerateRequest(
            project_id=agent_context["project_id"],
            requirement_text="保存权限测试",
        ),
    )
    await wait_for_functional_session(result.id, agent_context["viewer"])

    with pytest.raises(AppException) as exc:
        await FunctionalAgentService.save(
            agent_context["viewer"],
            result.id,
            FunctionalSaveRequest(
                catalog_id=agent_context["func_catalog_id"],
                case_indexes=[0],
            ),
        )
    assert exc.value.code == 403


@pytest.mark.asyncio
async def test_functional_editor_can_save(agent_context):
    result = await FunctionalAgentService.generate(
        agent_context["viewer"],
        FunctionalGenerateRequest(
            project_id=agent_context["project_id"],
            requirement_text="编辑者保存测试",
        ),
    )
    await wait_for_functional_session(result.id, agent_context["viewer"])

    save_result = await FunctionalAgentService.save(
        agent_context["editor"],
        result.id,
        FunctionalSaveRequest(
            catalog_id=agent_context["func_catalog_id"],
            case_indexes=[0],
        ),
    )
    assert save_result.created_case_ids
    assert save_result.created_test_point_ids == []


@pytest.mark.asyncio
async def test_api_generate_from_interface(agent_context):
    result = await ApiAgentService.generate_from_interface(
        agent_context["viewer"],
        ApiGenerateFromInterfaceRequest(
            interface_id=agent_context["interface_id"],
            environment_id=agent_context["environment_id"],
        ),
    )
    assert result.session_id
    assert len(result.base_cases) >= 1


@pytest.mark.asyncio
async def test_api_generate_from_doc_and_confirm(agent_context):
    doc = "Path: /agent/confirm\nMethod: POST\n接口描述: confirm flow"
    preview = await ApiAgentService.generate_from_doc(
        agent_context["viewer"],
        ApiGenerateFromDocRequest(
            project_id=agent_context["project_id"],
            api_doc_text=doc,
        ),
    )

    result = await ApiAgentService.confirm(
        agent_context["editor"],
        ApiConfirmRequest(
            session_id=preview.session_id,
            selected_indexes=[0],
            environment_id=agent_context["environment_id"],
            catalog_id=agent_context["api_catalog_id"],
        ),
    )
    assert result.created_interface_id
    assert result.created_case_ids
    assert result.created_base_case_ids


@pytest.mark.asyncio
async def test_api_viewer_cannot_confirm(agent_context):
    doc = "Path: /agent/deny\nMethod: GET\n接口描述: deny confirm"
    preview = await ApiAgentService.generate_from_doc(
        agent_context["viewer"],
        ApiGenerateFromDocRequest(
            project_id=agent_context["project_id"],
            api_doc_text=doc,
        ),
    )

    with pytest.raises(AppException) as exc:
        await ApiAgentService.confirm(
            agent_context["viewer"],
            ApiConfirmRequest(
                session_id=preview.session_id,
                selected_indexes=[0],
                environment_id=agent_context["environment_id"],
                catalog_id=agent_context["api_catalog_id"],
            ),
        )
    assert exc.value.code == 403
