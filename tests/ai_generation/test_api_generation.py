import pytest

from service.ai_generation.models import AIGenerationSession
from service.api_test.case.generation_service import GenerationService
from service.api_test.case.schemas import ApiConfirmRequest, PreviewFromDocRequest
from service.api_test.interface.interface_service import InterfaceService
from service.api_test.interface.models import ApiInterface
from service.api_test.interface.schemas import InterfaceCreateRequest
from service.core.enums import GenType, InputRefType, SessionStatus
from service.core.exceptions import AppException


@pytest.mark.asyncio
async def test_preview_from_doc_creates_session(api_gen_context):
    user = api_gen_context["user"]
    project_id = api_gen_context["project_id"]
    doc = "Path: /preview/doc\nMethod: POST\n接口描述: test"

    result = await GenerationService.preview_from_doc(
        user,
        PreviewFromDocRequest(
            project_id=project_id,
            api_doc_text=doc,
            user_prompt="focus on edge cases",
        ),
    )

    assert result.session_id
    assert len(result.base_cases) >= 1

    session = await GenerationService.get_session(user, result.session_id)
    assert session.status == SessionStatus.success
    assert session.output_payload is not None
    assert session.output_payload["api_doc"] == doc

    row = await AIGenerationSession.get(id=result.session_id)
    assert row.gen_type == GenType.api_base
    assert row.input_ref_type == InputRefType.api_doc
    assert row.prompt_hash


@pytest.mark.asyncio
async def test_confirm_from_doc_creates_interface(api_gen_context):
    user = api_gen_context["user"]
    project_id = api_gen_context["project_id"]
    catalog_id = api_gen_context["catalog_id"]
    environment_id = api_gen_context["environment_id"]
    doc = "Path: /agent/create\nMethod: POST\n接口描述: create from doc"

    preview = await GenerationService.preview_from_doc(
        user,
        PreviewFromDocRequest(project_id=project_id, api_doc_text=doc),
    )

    result = await GenerationService.confirm_session(
        user,
        ApiConfirmRequest(
            session_id=preview.session_id,
            selected_indexes=[0],
            environment_id=environment_id,
            catalog_id=catalog_id,
        ),
    )

    assert result.created_interface_id is not None
    assert result.created_case_ids
    assert result.created_base_case_ids

    iface = await ApiInterface.get_or_none(
        id=result.created_interface_id, is_current=True
    )
    assert iface is not None
    assert iface.method == "POST"
    assert iface.path == "/agent/create"
    assert iface.catalog_id == catalog_id


@pytest.mark.asyncio
async def test_confirm_from_doc_method_path_conflict_409(api_gen_context):
    user = api_gen_context["user"]
    project_id = api_gen_context["project_id"]
    catalog_id = api_gen_context["catalog_id"]
    environment_id = api_gen_context["environment_id"]
    conflict_path = "/agent/conflict"
    doc = f"Path: {conflict_path}\nMethod: GET\n接口描述: conflict"

    await InterfaceService.create(
        user,
        InterfaceCreateRequest(
            project_id=project_id,
            catalog_id=catalog_id,
            method="GET",
            path=conflict_path,
            summary="existing",
            parameters={"header": [], "path": [], "query": []},
            responses=[],
        ),
    )

    preview = await GenerationService.preview_from_doc(
        user,
        PreviewFromDocRequest(project_id=project_id, api_doc_text=doc),
    )

    with pytest.raises(AppException) as exc:
        await GenerationService.confirm_session(
            user,
            ApiConfirmRequest(
                session_id=preview.session_id,
                selected_indexes=[0],
                environment_id=environment_id,
                catalog_id=catalog_id,
            ),
        )

    assert exc.value.code == 409
