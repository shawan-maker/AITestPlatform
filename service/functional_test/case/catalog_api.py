"""功能测试模块 - case/catalog_api

API 路由端点
"""
from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.response import success
from service.functional_test.case.catalog_service import CatalogService
from service.functional_test.case.schemas import (
    CatalogCreateRequest,
    CatalogMoveRequest,
    CatalogUpdateRequest,
)
from service.user.models import User

router = APIRouter(tags=["功能测试-用例目录"])


@router.get("/case-catalogs/tree", summary="用例目录树")
async def get_catalog_tree(
    project_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.get_tree(user, project_id)
    return success(data=data)


@router.post("/case-catalogs", summary="创建用例目录")
async def create_catalog(
    body: CatalogCreateRequest,
    project_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.create(user, project_id, body)
    return success(data=data, message="目录创建成功")


@router.patch("/case-catalogs/{catalog_id}", summary="更新用例目录")
async def update_catalog(
    catalog_id: int,
    body: CatalogUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.update(user, catalog_id, body)
    return success(data=data, message="目录更新成功")


@router.delete("/case-catalogs/{catalog_id}", summary="删除用例目录")
async def delete_catalog(
    catalog_id: int,
    user: User = Depends(get_current_active_user),
):
    await CatalogService.delete(user, catalog_id)
    return success(message="目录删除成功")


@router.post("/case-catalogs/{catalog_id}/move", summary="移动用例目录")
async def move_catalog(
    catalog_id: int,
    body: CatalogMoveRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CatalogService.move(user, catalog_id, body)
    return success(data=data, message="目录移动成功")
