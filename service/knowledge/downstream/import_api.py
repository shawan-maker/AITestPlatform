from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.response import success
from service.knowledge.downstream.import_service import ImportService
from service.knowledge.downstream.schemas import ImportInterfacesRequest
from service.user.models import User

router = APIRouter()


@router.post(
    "/documents/{document_id}/versions/{version_id}/import-interfaces/preview",
    summary="预览解析接口列表",
)
async def preview_import_interfaces(
    document_id: int,
    version_id: int,
    catalog_id: int | None = Query(default=None, description="目标目录ID，用于目录范围冲突检测"),
    user: User = Depends(get_current_active_user),
):
    data = await ImportService.preview_interfaces(user, document_id, version_id, catalog_id=catalog_id)
    return success(data=data)


@router.post(
    "/documents/{document_id}/versions/{version_id}/import-interfaces",
    summary="从解析结果导入接口",
)
async def import_interfaces(
    document_id: int,
    version_id: int,
    body: ImportInterfacesRequest,
    user: User = Depends(get_current_active_user),
):
    data = await ImportService.import_interfaces(
        user, document_id, version_id, body
    )
    return success(data=data, message="接口导入完成")
