from fastapi import APIRouter, Depends, Query

from service.api_test.catalog.catalog_service import CatalogService
from service.api_test.catalog.schemas import (
    CatalogCreateRequest,
    CatalogMoveRequest,
    CatalogUpdateRequest,
)
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(tags=["接口测试-目录"])


@router.get("/catalogs/tree", summary="接口目录树")
async def get_catalog_tree(
    project_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.get_tree(user, project_id)
    return success(data=data)


@router.post("/catalogs", summary="创建接口目录")
async def create_catalog(
    body: CatalogCreateRequest,
    project_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.create(user, project_id, body)
    return success(data=data, message="目录创建成功")


@router.patch("/catalogs/{catalog_id}", summary="更新接口目录")
async def update_catalog(
    catalog_id: int,
    body: CatalogUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.update(user, catalog_id, body)
    return success(data=data, message="目录更新成功")


@router.delete("/catalogs/{catalog_id}", summary="删除接口目录")
async def delete_catalog(
    catalog_id: int,
    user: User = Depends(get_current_active_user),
):
    await CatalogService.delete(user, catalog_id)
    return success(message="目录删除成功")


@router.post("/catalogs/{catalog_id}/move", summary="移动接口目录")
async def move_catalog(
    catalog_id: int,
    body: CatalogMoveRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.move(user, catalog_id, body)
    return success(data=data, message="目录移动成功")
