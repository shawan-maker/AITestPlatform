"""测试环境管理模块 - variable/catalog_api

API 路由端点
"""
from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user, require_project_editor, require_project_viewer
from service.core.response import success
from service.test_environment.variable.catalog_service import CatalogService
from service.test_environment.variable.schemas import CatalogCreateRequest, CatalogUpdateRequest
from service.user.models import User

router = APIRouter(prefix="/catalogs", tags=["环境-目录"])


@router.get("/tree", summary="目录树")
async def get_catalog_tree(
    project_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.get_tree(user, project_id)
    return success(data=data)


@router.post("", summary="创建目录")
async def create_catalog(
    data: CatalogCreateRequest,
    project_id: int = Query(..., ge=1),
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    result = await CatalogService.create(user, project_id, data)
    return success(data=result, message="目录创建成功")


@router.patch("/{catalog_id}", summary="更新目录")
async def update_catalog(
    catalog_id: int,
    data: CatalogUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await CatalogService.update(user, catalog_id, data)
    return success(data=result, message="目录更新成功")


@router.delete("/{catalog_id}", summary="删除目录")
async def delete_catalog(
    catalog_id: int,
    user: User = Depends(get_current_active_user),
):
    await CatalogService.delete(user, catalog_id)
    return success(message="目录已删除")
