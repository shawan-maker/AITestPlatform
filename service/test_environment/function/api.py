from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user, require_environment_editor
from service.core.response import success
from service.test_environment.function.service import FunctionFileService
from service.test_environment.function.schemas import (
    EnvironmentFunctionBindRequest,
    FunctionDebugRequest,
    FunctionFileCreateRequest,
    FunctionFileUpdateRequest,
    FunctionValidateRequest,
)
from service.user.models import User

router = APIRouter(prefix="/function-files", tags=["环境-函数文件"])


@router.get("", summary="函数文件列表")
async def list_function_files(
    project_id: int | None = Query(None, ge=1),
    bound: bool | None = Query(None),
    keyword: str | None = Query(None),
    method_name: str | None = Query(None, description="方法名模糊搜索"),
    environment_id: int | None = Query(None, ge=1, description="绑定变量文件 ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await FunctionFileService.list_files(
        user,
        project_id=project_id,
        bound=bound,
        keyword=keyword,
        method_name=method_name,
        environment_id=environment_id,
        page=page,
        page_size=page_size,
    )
    return success(data=data)


@router.get("/bound-environments", summary="已绑定函数的变量文件选项")
async def list_function_bound_environments(
    project_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await FunctionFileService.list_bound_environment_options(user, project_id)
    return success(data=data)


@router.post("", summary="创建函数文件")
async def create_function_file(
    data: FunctionFileCreateRequest,
    project_id: int | None = Query(None, ge=1),
    user: User = Depends(get_current_active_user),
):
    result = await FunctionFileService.create(user, data, project_id=project_id)
    return success(data=result, message="函数文件创建成功")


@router.post("/validate", summary="校验函数源码语法")
async def validate_function_file(
    data: FunctionValidateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await FunctionFileService.validate_source(data.file_name, data.source_code)
    return success(data=result, message="语法校验通过")


@router.post("/{file_id}/debug", summary="调试执行函数")
async def debug_function_file(
    file_id: int,
    data: FunctionDebugRequest,
    user: User = Depends(get_current_active_user),
):
    result = await FunctionFileService.debug(user, file_id, data)
    return success(data=result)


@router.get("/{file_id}", summary="函数文件详情")
async def get_function_file(
    file_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await FunctionFileService.get_detail(user, file_id)
    return success(data=data)


@router.patch("/{file_id}", summary="更新函数文件")
async def update_function_file(
    file_id: int,
    data: FunctionFileUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await FunctionFileService.update(user, file_id, data)
    return success(data=result, message="函数文件更新成功")


@router.delete("/{file_id}", summary="删除函数文件")
async def delete_function_file(
    file_id: int,
    user: User = Depends(get_current_active_user),
):
    await FunctionFileService.delete(user, file_id)
    return success(message="函数文件已删除")


bind_router = APIRouter(tags=["环境-函数文件"])


@bind_router.put("/environments/{environment_id}/function-files", summary="绑定函数文件")
async def bind_function_files(
    environment_id: int,
    data: EnvironmentFunctionBindRequest,
    _: object = Depends(require_environment_editor),
    user: User = Depends(get_current_active_user),
):
    result = await FunctionFileService.bind_to_environment(user, environment_id, data)
    return success(data=result, message="绑定已更新")
