from service.ai_generation.common import load_knowledge_requirement_text
from service.ai_generation.permissions import ensure_agent_editor, ensure_agent_viewer
from service.ai_generation.schemas import (
    AIGenerationSessionOut,
    FunctionalGenerateRequest,
    FunctionalPreviewUpdateRequest,
    FunctionalSaveRequest,
    GenerationSaveResult,
)
from service.ai_generation.session_schemas import AIGenerationPreviewUpdateRequest
from service.functional_test.case.generation_service import FunctionalCaseGenerationService
from service.functional_test.case.schemas import (
    GenerationSaveRequest,
    GenerationSessionCreateRequest,
)
from service.user.models import User


class FunctionalAgentService:
    @classmethod
    async def generate(
        cls,
        user: User,
        body: FunctionalGenerateRequest,
    ) -> AIGenerationSessionOut:
        await ensure_agent_viewer(body.project_id, user)
        if body.knowledge_document_id is not None:
            text = await load_knowledge_requirement_text(
                body.knowledge_document_id, body.project_id
            )
            req = GenerationSessionCreateRequest(
                project_id=body.project_id,
                requirement_text=text,
                knowledge_document_id=body.knowledge_document_id,
                user_prompt=body.user_prompt,
                module_id=body.module_id,
            )
        else:
            req = GenerationSessionCreateRequest(
                project_id=body.project_id,
                requirement_text=body.requirement_text,
                user_prompt=body.user_prompt,
                module_id=body.module_id,
            )
        return await FunctionalCaseGenerationService.create_session(user, req)

    @classmethod
    async def get_session(
        cls,
        user: User,
        session_id: int,
    ) -> AIGenerationSessionOut:
        return await FunctionalCaseGenerationService.get_session(user, session_id)

    @classmethod
    async def update_preview(
        cls,
        user: User,
        session_id: int,
        body: FunctionalPreviewUpdateRequest,
    ) -> AIGenerationSessionOut:
        return await FunctionalCaseGenerationService.update_preview(
            user,
            session_id,
            AIGenerationPreviewUpdateRequest(output_payload=body.output_payload),
        )

    @classmethod
    async def save(
        cls,
        user: User,
        session_id: int,
        body: FunctionalSaveRequest,
    ) -> GenerationSaveResult:
        session = await FunctionalCaseGenerationService._get_session_or_404(session_id)
        await ensure_agent_editor(session.project_id, user)
        return await FunctionalCaseGenerationService.save_cases(
            user,
            session_id,
            GenerationSaveRequest(
                catalog_id=body.catalog_id,
                case_indexes=body.case_indexes,
            ),
        )
