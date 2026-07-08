"""功能测试模块 - case/generation_api

API 路由端点
"""
from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user
from service.core.response import success
from service.functional_test.case.generation_service import FunctionalCaseGenerationService
from service.functional_test.case.schemas import (
    GenerationPreviewUpdateRequest,
    GenerationSaveRequest,
    GenerationSessionCreateRequest,
)
from service.user.models import User

router = APIRouter(prefix="/case-generation", tags=["legacy-case-generation", "功能测试-AI生成"])


@router.post("/sessions", summary="创建功能用例生成会话", deprecated=True)
async def create_generation_session(
    body: GenerationSessionCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalCaseGenerationService.create_session(user, body)
    return success(data=data, message="生成会话已创建")


@router.get("/sessions/{session_id}", summary="查询生成会话", deprecated=True)
async def get_generation_session(
    session_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalCaseGenerationService.get_session(user, session_id)
    return success(data=data)


@router.patch("/sessions/{session_id}/preview", summary="编辑生成预览", deprecated=True)
async def update_generation_preview(
    session_id: int,
    body: GenerationPreviewUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalCaseGenerationService.update_preview(user, session_id, body)
    return success(data=data, message="预览已更新")


@router.post("/sessions/{session_id}/save", summary="保存勾选用例", deprecated=True)
async def save_generation_cases(
    session_id: int,
    body: GenerationSaveRequest,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionalCaseGenerationService.save_cases(user, session_id, body)
    return success(data=data, message="用例保存成功")
