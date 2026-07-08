"""接口测试模块 - interface/interface_api

API 路由端点
"""
from fastapi import APIRouter, Depends, Query

from service.api_test.interface.import_service import ImportService
from service.api_test.interface.interface_service import InterfaceService
from service.api_test.interface.schemas import (
    ImportConfirmRequest,
    InterfaceBatchDeleteRequest,
    InterfaceCreateRequest,
    InterfaceListQuery,
    InterfaceReorderRequest,
    InterfaceUpdateRequest,
)
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(tags=["接口测试-接口"])


@router.get("/interfaces", summary="搜索接口列表")
async def list_interfaces(
    project_id: int = Query(..., ge=1),
    catalog_id: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_active_user),
):
    query = InterfaceListQuery(
        project_id=project_id,
        catalog_id=catalog_id,
        q=q,
        page=page,
        page_size=page_size,
    )
    data = await InterfaceService.list_interfaces(user, query)
    return success(data=data)


@router.get("/catalogs/{catalog_id}/interfaces", summary="目录下接口列表")
async def list_catalog_interfaces(
    catalog_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    user: User = Depends(get_current_active_user),
):
    data = await InterfaceService.list_by_catalog(
        user, catalog_id, page=page, page_size=page_size
    )
    return success(data=data)


@router.post("/interfaces", summary="手工新建接口")
async def create_interface(
    body: InterfaceCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await InterfaceService.create(user, body)
    return success(data=data, message="接口创建成功")


@router.get("/interfaces/{interface_id}", summary="接口详情")
async def get_interface(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await InterfaceService.get_detail(user, interface_id)
    return success(data=data)


@router.patch("/interfaces/{interface_id}", summary="更新接口")
async def update_interface(
    interface_id: int,
    body: InterfaceUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await InterfaceService.update(user, interface_id, body)
    return success(data=data, message="接口更新成功")


@router.post("/interfaces/batch-delete", summary="批量删除接口")
async def batch_delete_interfaces(
    body: InterfaceBatchDeleteRequest,
    user: User = Depends(get_current_active_user),
):
    result = await InterfaceService.batch_delete(user, body)
    return success(data=result)


@router.delete("/interfaces/{interface_id}", summary="删除接口")
async def delete_interface(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    await InterfaceService.delete(user, interface_id)
    return success(message="接口删除成功")


@router.post("/interfaces/{interface_id}/copy", summary="复制接口")
async def copy_interface(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await InterfaceService.copy(user, interface_id)
    return success(data=data, message="接口复制成功")


@router.post("/interfaces/reorder", summary="接口排序/跨目录移动")
async def reorder_interfaces(
    body: InterfaceReorderRequest,
    user: User = Depends(get_current_active_user),
):
    await InterfaceService.reorder(user, body)
    return success(message="排序更新成功")


@router.get("/imports/preview", summary="导入预览")
async def import_preview(
    document_id: int = Query(..., ge=1),
    version_id: int = Query(..., ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await ImportService.preview(user, document_id, version_id)
    return success(data=data)


@router.post("/imports/confirm", summary="确认导入")
async def import_confirm(
    body: ImportConfirmRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ImportService.confirm(user, body)
    return success(data=data, message="导入完成")
