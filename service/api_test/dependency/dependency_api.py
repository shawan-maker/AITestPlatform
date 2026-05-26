from fastapi import APIRouter, Depends

from service.api_test.dependency.dependency_schemas import DependencyReplaceRequest
from service.api_test.dependency.dependency_service import DependencyService
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(tags=["接口测试-依赖"])


@router.get("/interfaces/{interface_id}/doc-preview", summary="接口文档预览")
async def doc_preview(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DependencyService.get_doc_preview(user, interface_id)
    return success(data=data)


@router.get("/interfaces/{interface_id}/dependencies", summary="依赖链列表")
async def list_dependencies(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DependencyService.list_dependencies(user, interface_id)
    return success(data=data)


@router.put("/interfaces/{interface_id}/dependencies", summary="手工保存依赖链")
async def replace_dependencies(
    interface_id: int,
    body: DependencyReplaceRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DependencyService.replace_dependencies(user, interface_id, body)
    return success(data=data, message="依赖链已保存")


@router.post(
    "/interfaces/{interface_id}/dependencies/reanalyze", summary="重新分析依赖"
)
async def reanalyze_dependencies(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DependencyService.reanalyze(user, interface_id)
    return success(data=data, message="依赖分析完成")
