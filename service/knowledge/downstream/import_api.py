from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user
from service.core.response import success
from service.knowledge.downstream.import_service import ImportService
from service.knowledge.downstream.schemas import ImportInterfacesRequest
from service.user.models import User

router = APIRouter()


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
        user,
        document_id,
        version_id,
        body.module_id,
        import_mode=body.import_mode,
    )
    return success(data=data, message="接口导入完成")
