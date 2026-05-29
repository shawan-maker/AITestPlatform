from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user, require_project_editor, require_project_viewer
from service.core.response import success
from service.test_environment.variable.global_config_service import ProjectGlobalConfigService
from service.test_environment.variable.schemas import ConfigGroupReplaceRequest, ConfigItemUpdateRequest
from service.user.models import User

router = APIRouter(tags=["环境-全局变量"])


@router.get("/projects/{project_id}/global-configs", summary="项目全局变量列表")
async def list_global_configs(
    project_id: int,
    _: tuple = Depends(require_project_viewer),
    user: User = Depends(get_current_active_user),
):
    data = await ProjectGlobalConfigService.list_configs(user, project_id)
    return success(data=data)


@router.put("/projects/{project_id}/global-configs", summary="批量覆盖项目全局变量")
async def replace_global_configs(
    project_id: int,
    data: ConfigGroupReplaceRequest,
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    result = await ProjectGlobalConfigService.replace_all(user, project_id, data)
    return success(data=result, message="全局变量已更新")


@router.patch("/global-configs/{config_id}", summary="更新全局变量项")
async def update_global_config(
    config_id: int,
    data: ConfigItemUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await ProjectGlobalConfigService.update_item(user, config_id, data)
    return success(data=result, message="全局变量已更新")


@router.delete("/global-configs/{config_id}", summary="删除全局变量项")
async def delete_global_config(
    config_id: int,
    user: User = Depends(get_current_active_user),
):
    await ProjectGlobalConfigService.delete_item(user, config_id)
    return success(message="全局变量已删除")
