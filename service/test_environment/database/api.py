from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user, require_environment_editor
from service.core.response import success
from service.test_environment.database.service import DbConnectionService
from service.test_environment.database.schemas import (
    DbConnectionCreateRequest,
    DbConnectionUpdateRequest,
    EnvironmentDbBindRequest,
)
from service.user.models import User

router = APIRouter(prefix="/db-connections", tags=["环境-数据库连接"])


@router.get("", summary="数据库连接列表")
async def list_db_connections(
    project_id: int | None = Query(None, ge=1),
    bound: bool | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await DbConnectionService.list_connections(
        user,
        project_id=project_id,
        bound=bound,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return success(data=data)


@router.post("", summary="创建数据库连接")
async def create_db_connection(
    data: DbConnectionCreateRequest,
    project_id: int | None = Query(None, ge=1),
    user: User = Depends(get_current_active_user),
):
    result = await DbConnectionService.create(user, data, project_id=project_id)
    return success(data=result, message="数据库连接创建成功")


@router.get("/{connection_id}", summary="数据库连接详情")
async def get_db_connection(
    connection_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DbConnectionService.get_detail(user, connection_id)
    return success(data=data)


@router.patch("/{connection_id}", summary="更新数据库连接")
async def update_db_connection(
    connection_id: int,
    data: DbConnectionUpdateRequest,
    project_id: int | None = Query(None, ge=1),
    user: User = Depends(get_current_active_user),
):
    result = await DbConnectionService.update(
        user, connection_id, data, project_id=project_id
    )
    return success(data=result, message="数据库连接更新成功")


@router.delete("/{connection_id}", summary="删除数据库连接")
async def delete_db_connection(
    connection_id: int,
    user: User = Depends(get_current_active_user),
):
    await DbConnectionService.delete(user, connection_id)
    return success(message="数据库连接已删除")


@router.post("/{connection_id}/test", summary="测试数据库连接")
async def test_db_connection(
    connection_id: int,
    user: User = Depends(get_current_active_user),
):
    result = await DbConnectionService.test_connection(user, connection_id)
    return success(data=result)


@router.get("/{connection_id}/test-logs", summary="连接测试历史")
async def list_test_logs(
    connection_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await DbConnectionService.list_test_logs(
        user, connection_id, page=page, page_size=page_size
    )
    return success(data=data)


bind_router = APIRouter(tags=["环境-数据库连接"])


@bind_router.put("/environments/{environment_id}/db-connections", summary="绑定数据库连接")
async def bind_db_connections(
    environment_id: int,
    data: EnvironmentDbBindRequest,
    _: object = Depends(require_environment_editor),
    user: User = Depends(get_current_active_user),
):
    result = await DbConnectionService.bind_to_environment(user, environment_id, data)
    return success(data=result, message="绑定已更新")
