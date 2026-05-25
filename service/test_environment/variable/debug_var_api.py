from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user, require_environment_editor, require_environment_viewer
from service.core.enums import DebugVarSource
from service.core.response import success
from service.test_environment.variable.debug_service import DebugRuntimeVarService
from service.test_environment.variable.schemas import (
    DebugVarBatchUpsertRequest,
    DebugVarItem,
    DebugVarSyncRequest,
)
from service.user.models import User

router = APIRouter(tags=["环境-调试变量"])


@router.get("/environments/{environment_id}/debug-vars", summary="调试变量列表")
async def list_debug_vars(
    environment_id: int,
    _: object = Depends(require_environment_viewer),
    user: User = Depends(get_current_active_user),
):
    data = await DebugRuntimeVarService.list_vars(user, environment_id)
    return success(data=data)


@router.put("/environments/{environment_id}/debug-vars", summary="批量 upsert 调试变量")
async def upsert_debug_vars(
    environment_id: int,
    data: DebugVarBatchUpsertRequest,
    _: object = Depends(require_environment_editor),
    user: User = Depends(get_current_active_user),
):
    result = await DebugRuntimeVarService.batch_upsert(user, environment_id, data)
    return success(data=result, message="调试变量已更新")


@router.post(
    "/environments/{environment_id}/debug-vars/sync",
    summary="引擎回写调试变量",
)
async def sync_debug_vars(
    environment_id: int,
    data: DebugVarSyncRequest,
    _: object = Depends(require_environment_editor),
    user: User = Depends(get_current_active_user),
):
    upsert = DebugVarBatchUpsertRequest(
        items=[
            DebugVarItem(
                var_key=item.var_key,
                var_value=item.var_value,
                source=DebugVarSource.engine,
            )
            for item in data.items
        ]
    )
    result = await DebugRuntimeVarService.batch_upsert(user, environment_id, upsert)
    return success(data=result, message="调试变量已同步")


@router.delete("/debug-vars/{var_id}", summary="删除调试变量")
async def delete_debug_var(
    var_id: int,
    user: User = Depends(get_current_active_user),
):
    await DebugRuntimeVarService.delete_var(user, var_id)
    return success(message="调试变量已删除")
