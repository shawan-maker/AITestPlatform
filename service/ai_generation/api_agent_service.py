from service.ai_generation.models import AIGenerationSession
from service.ai_generation.permissions import ensure_agent_editor, ensure_agent_viewer
from service.ai_generation.schemas import (
    AIGenerationSessionOut,
    ApiConfirmRequest,
    ApiConfirmResult,
    ApiGenerateFromDocRequest,
    ApiGenerateFromInterfaceRequest,
    ApiSessionPreviewUpdateRequest,
    GeneratePreviewResult,
)
from service.api_test.case.generation_service import ApiCaseGenerationService
from service.api_test.case.schemas import (
    GeneratePreviewRequest,
    PreviewFromDocRequest,
)
from service.api_test.interface.interface_service import InterfaceService
from service.core.exceptions import AppException
from service.user.models import User


class ApiAgentService:
    @classmethod
    async def generate_from_interface(
        cls,
        user: User,
        body: ApiGenerateFromInterfaceRequest,
    ) -> GeneratePreviewResult:
        iface = await InterfaceService._get_current_or_404(body.interface_id)
        await ensure_agent_viewer(iface.project_id, user)
        return await ApiCaseGenerationService.preview(
            user,
            body.interface_id,
            GeneratePreviewRequest(
                environment_id=body.environment_id,
                user_prompt=body.user_prompt,
            ),
        )

    @classmethod
    async def generate_from_doc(
        cls,
        user: User,
        body: ApiGenerateFromDocRequest,
    ) -> GeneratePreviewResult:
        await ensure_agent_viewer(body.project_id, user)
        return await ApiCaseGenerationService.preview_from_doc(
            user,
            PreviewFromDocRequest(
                project_id=body.project_id,
                api_doc_text=body.api_doc_text,
                user_prompt=body.user_prompt,
                module_id=body.module_id,
            ),
        )

    @classmethod
    async def get_session(
        cls,
        user: User,
        session_id: int,
    ) -> AIGenerationSessionOut:
        return await ApiCaseGenerationService.get_session(user, session_id)

    @classmethod
    async def update_preview(
        cls,
        user: User,
        session_id: int,
        body: ApiSessionPreviewUpdateRequest,
    ) -> AIGenerationSessionOut:
        return await ApiCaseGenerationService.update_preview(user, session_id, body)

    @classmethod
    async def confirm(
        cls,
        user: User,
        body: ApiConfirmRequest,
    ) -> ApiConfirmResult:
        session = await AIGenerationSession.get_or_none(id=body.session_id)
        if session is None:
            raise AppException("生成会话不存在", 404)
        await ensure_agent_editor(session.project_id, user)
        return await ApiCaseGenerationService.confirm_session(user, body)
