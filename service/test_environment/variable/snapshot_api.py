"""测试环境管理模块 - variable/snapshot_api

API 路由端点
"""
from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user, require_environment_editor, require_environment_viewer
from service.core.exceptions import AppException
from service.core.response import success
from service.test_environment.variable.schemas import SnapshotCreateRequest
from service.test_environment.variable.snapshot_service import SnapshotService
from service.user.models import User

router = APIRouter(tags=["环境-快照"])


@router.get("/environments/{environment_id}/snapshots", summary="快照列表（报告/内部）")
async def list_snapshots(
    environment_id: int,
    _: object = Depends(require_environment_viewer),
    user: User = Depends(get_current_active_user),
):
    data = await SnapshotService.list_snapshots(user, environment_id)
    return success(data=data)


@router.post("/environments/{environment_id}/snapshots", summary="生成快照（已禁用，仅 trigger 内部）")
async def create_snapshot(
    environment_id: int,
    data: SnapshotCreateRequest = SnapshotCreateRequest(),
    _: object = Depends(require_environment_editor),
    user: User = Depends(get_current_active_user),
):
    raise AppException("快照由任务/套件运行时自动创建，不支持手工生成", 403)


@router.get("/snapshots/{snapshot_id}", summary="快照详情")
async def get_snapshot(
    snapshot_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await SnapshotService.get_detail(user, snapshot_id)
    return success(data=data)


@router.put("/snapshots/{snapshot_id}/activate", summary="激活快照（已废弃）")
async def activate_snapshot(
    snapshot_id: int,
    user: User = Depends(get_current_active_user),
):
    raise AppException("is_active 已废弃，快照与 run 绑定", 403)


@router.delete("/snapshots/{snapshot_id}", summary="删除快照")
async def delete_snapshot(
    snapshot_id: int,
    user: User = Depends(get_current_active_user),
):
    await SnapshotService.delete(user, snapshot_id)
    return success(message="快照已删除")
