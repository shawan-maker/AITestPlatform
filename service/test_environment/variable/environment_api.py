from fastapi import APIRouter, Depends, Query

from service.core.deps import (
    get_current_active_user,
    require_environment_editor,
    require_environment_viewer,
    require_project_editor,
    require_project_viewer,
)
from service.core.response import success
from service.test_environment.variable.config_service import EnvironmentConfigService
from service.test_environment.variable.environment_service import EnvironmentService
from service.test_environment.variable.schemas import (
    ConfigGroupReplaceRequest,
    ConfigItemCreateRequest,
    ConfigItemUpdateRequest,
    EnvironmentCreateRequest,
    EnvironmentUpdateRequest,
)
from service.test_environment.variable.assembler import TestEnvDataAssembler
from service.user.models import User

router = APIRouter(tags=["环境-变量文件"])


@router.get("/environments", summary="变量文件列表")
async def list_environments(
    project_id: int = Query(..., ge=1),
    catalog_id: int | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: tuple = Depends(require_project_viewer),
    user: User = Depends(get_current_active_user),
):
    data = await EnvironmentService.list_environments(
        user, project_id, catalog_id=catalog_id, keyword=keyword, page=page, page_size=page_size
    )
    return success(data=data)


@router.post("/environments", summary="创建变量文件")
async def create_environment(
    data: EnvironmentCreateRequest,
    project_id: int = Query(..., ge=1),
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    result = await EnvironmentService.create(user, project_id, data)
    return success(data=result, message="变量文件创建成功")


@router.get("/environments/{environment_id}", summary="变量文件详情")
async def get_environment(
    environment_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await EnvironmentService.get_detail(user, environment_id)
    return success(data=data)


@router.patch("/environments/{environment_id}", summary="更新变量文件")
async def update_environment(
    environment_id: int,
    data: EnvironmentUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await EnvironmentService.update(user, environment_id, data)
    return success(data=result, message="变量文件更新成功")


@router.delete("/environments/{environment_id}", summary="删除变量文件")
async def delete_environment(
    environment_id: int,
    user: User = Depends(get_current_active_user),
):
    await EnvironmentService.delete(user, environment_id)
    return success(message="变量文件已删除")


@router.get("/environments/{environment_id}/configs", summary="配置列表")
async def list_configs(
    environment_id: int,
    config_group: str | None = Query(None),
    _: object = Depends(require_environment_viewer),
    user: User = Depends(get_current_active_user),
):
    data = await EnvironmentConfigService.list_configs(user, environment_id, config_group)
    return success(data=data)


@router.put("/environments/{environment_id}/configs/{config_group}", summary="整组覆盖配置")
async def replace_config_group(
    environment_id: int,
    config_group: str,
    data: ConfigGroupReplaceRequest,
    _: object = Depends(require_environment_editor),
    user: User = Depends(get_current_active_user),
):
    result = await EnvironmentConfigService.replace_group(
        user, environment_id, config_group, data
    )
    return success(data=result, message="配置已更新")


@router.post("/environments/{environment_id}/configs", summary="新增配置项")
async def create_config(
    environment_id: int,
    data: ConfigItemCreateRequest,
    _: object = Depends(require_environment_editor),
    user: User = Depends(get_current_active_user),
):
    result = await EnvironmentConfigService.create_item(user, environment_id, data)
    return success(data=result, message="配置项创建成功")


@router.patch("/configs/{config_id}", summary="更新配置项")
async def update_config(
    config_id: int,
    data: ConfigItemUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await EnvironmentConfigService.update_item(user, config_id, data)
    return success(data=result, message="配置项更新成功")


@router.delete("/configs/{config_id}", summary="删除配置项")
async def delete_config(
    config_id: int,
    user: User = Depends(get_current_active_user),
):
    await EnvironmentConfigService.delete_item(user, config_id)
    return success(message="配置项已删除")


@router.get("/environments/{environment_id}/test-env-data", summary="组装 test_env_data")
async def get_test_env_data(
    environment_id: int,
    _: object = Depends(require_environment_viewer),
    user: User = Depends(get_current_active_user),
):
    data = await TestEnvDataAssembler.get_test_env_data(environment_id)
    if data.get("db"):
        for item in data["db"]:
            cfg = item.get("config") or {}
            if cfg.get("password"):
                cfg["password"] = "***"
    return success(data=data)
