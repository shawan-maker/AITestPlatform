from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from service.core.enums import GenType, SessionStatus
from service.core.exceptions import AppException
from service.functional_test.case.generation_service import FunctionalCaseGenerationService
from service.functional_test.case.schemas import (
    GenerationSaveRequest,
    GenerationSessionCreateRequest,
)


class TestValidateCreateInput:
    @pytest.mark.asyncio
    async def test_rejects_no_input_path(self):
        data = GenerationSessionCreateRequest(project_id=1)
        with pytest.raises(AppException) as exc:
            await FunctionalCaseGenerationService._validate_create_input(data)
        assert exc.value.code == 400
        assert "至少提供一个" in exc.value.message

    @pytest.mark.asyncio
    async def test_rejects_requirement_text_and_knowledge_document_id(self):
        data = GenerationSessionCreateRequest(
            project_id=1,
            requirement_text="some text",
            knowledge_document_id=10,
        )
        with pytest.raises(AppException) as exc:
            await FunctionalCaseGenerationService._validate_create_input(data)
        assert exc.value.code == 400
        assert "不能同时提供" in exc.value.message

    @pytest.mark.asyncio
    async def test_rejects_requirement_id_and_knowledge_document_id(self):
        data = GenerationSessionCreateRequest(
            project_id=1,
            requirement_id=5,
            knowledge_document_id=10,
        )
        with pytest.raises(AppException) as exc:
            await FunctionalCaseGenerationService._validate_create_input(data)
        assert exc.value.code == 400
        assert "不能同时提供" in exc.value.message

    @pytest.mark.asyncio
    async def test_accepts_knowledge_document_id_only(self):
        data = GenerationSessionCreateRequest(project_id=1, knowledge_document_id=10)
        await FunctionalCaseGenerationService._validate_create_input(data)

    @pytest.mark.asyncio
    async def test_accepts_requirement_text_only(self):
        data = GenerationSessionCreateRequest(project_id=1, requirement_text="req body")
        await FunctionalCaseGenerationService._validate_create_input(data)


class TestSaveCasesWithoutRequirement:
    @pytest.mark.asyncio
    async def test_skips_test_point_creation_when_no_requirement(self):
        session = MagicMock()
        session.project_id = 1
        session.module_id = None
        session.id = 99
        session.gen_type = GenType.functional
        session.status = SessionStatus.success
        session.input_ref_id = None
        session.output_payload = {
            "test_points": [{"type": "functional", "dimension": "d", "test_point": "tp"}],
            "cases": [
                {
                    "case_id": "TC-001",
                    "case_name": "case 1",
                    "priority": "P2",
                    "dimension": "d",
                    "preconditions": "",
                    "test_steps": "step",
                    "test_data": "",
                    "expected_result": "ok",
                    "actual_result": "",
                }
            ],
        }

        user = MagicMock()
        user.id = 1
        data = GenerationSaveRequest(catalog_id=1, case_indexes=[0])

        with (
            patch.object(
                FunctionalCaseGenerationService,
                "_get_session_or_404",
                new=AsyncMock(return_value=session),
            ),
            patch(
                "service.functional_test.case.generation_service.ensure_case_editor",
                new=AsyncMock(),
            ),
            patch(
                "service.functional_test.case.generation_service.CatalogService._get_catalog_or_404",
                new=AsyncMock(),
            ),
            patch(
                "service.functional_test.case.generation_service.CaseService._next_sort_order",
                new=AsyncMock(return_value=0),
            ),
            patch(
                "service.functional_test.case.generation_service.FunctionalTestPoint.create",
                new=AsyncMock(),
            ) as mock_tp_create,
            patch(
                "service.functional_test.case.generation_service.FunctionalCase.create",
                new=AsyncMock(return_value=MagicMock(id=1001)),
            ) as mock_case_create,
            patch(
                "service.functional_test.case.generation_service.in_transaction",
                return_value=MagicMock(
                    __aenter__=AsyncMock(return_value=None),
                    __aexit__=AsyncMock(return_value=False),
                ),
            ),
        ):
            result = await FunctionalCaseGenerationService.save_cases(user, 99, data)

        mock_tp_create.assert_not_called()
        mock_case_create.assert_called_once()
        assert mock_case_create.call_args.kwargs["test_point_id"] is None
        assert mock_case_create.call_args.kwargs["requirement_id"] is None
        assert result.created_test_point_ids == []
        assert result.created_case_ids == [1001]
