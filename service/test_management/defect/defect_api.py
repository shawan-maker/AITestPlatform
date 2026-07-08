"""测试管理模块 - defect/defect_api

API 路由端点
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.enums import DefectCategory, DefectPriority, DefectSeverity, DefectStatus
from service.core.response import success
from service.test_management.defect.defect_service import DefectService
from service.test_management.defect.schemas import (
    DefectBatchDeleteRequest,
    DefectCommentCreateRequest,
    DefectListQuery,
    DefectManualCreateRequest,
    DefectTransitionRequest,
    DefectUpdateRequest,
)
from service.user.models import User

router = APIRouter(prefix="/defects", tags=["测试管理-缺陷"])


@router.get("", summary="缺陷列表")
async def list_defects(
    project_id: int = Query(..., ge=1),
    q: str | None = Query(default=None),
    id: int | None = Query(default=None, ge=1),
    severity: DefectSeverity | None = Query(default=None),
    priority: DefectPriority | None = Query(default=None),
    status: DefectStatus | None = Query(default=None),
    defect_category: DefectCategory | None = Query(default=None),
    created_by_id: int | None = Query(default=None, ge=1),
    assignee_id: int | None = Query(default=None, ge=1),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    query = DefectListQuery(
        project_id=project_id,
        q=q,
        id=id,
        severity=severity,
        priority=priority,
        status=status,
        defect_category=defect_category,
        created_by_id=created_by_id,
        assignee_id=assignee_id,
        created_from=created_from,
        created_to=created_to,
        page=page,
        page_size=page_size,
    )
    data = await DefectService.list(user, query)
    return success(data=data)


@router.post("", summary="独立添加缺陷")
async def create_defect(
    body: DefectManualCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DefectService.create_manual(user, body)
    return success(data=data, message="缺陷创建成功")


@router.post("/batch-delete", summary="批量删除缺陷")
async def batch_delete(
    data: DefectBatchDeleteRequest,
    user: User = Depends(get_current_active_user),
):
    result = await DefectService.batch_delete(user, data)
    return success(data=result)


@router.get("/{defect_id}", summary="缺陷详情")
async def get_defect(
    defect_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DefectService.get_detail(user, defect_id)
    return success(data=data)


@router.patch("/{defect_id}", summary="编辑缺陷")
async def update_defect(
    defect_id: int,
    body: DefectUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DefectService.update(user, defect_id, body)
    return success(data=data, message="缺陷更新成功")


@router.post("/{defect_id}/transition", summary="处理缺陷（状态流转）")
async def transition_defect(
    defect_id: int,
    body: DefectTransitionRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DefectService.transition(user, defect_id, body)
    return success(data=data, message="缺陷状态已更新")


@router.post("/{defect_id}/comments", summary="新增评论")
async def add_defect_comment(
    defect_id: int,
    body: DefectCommentCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DefectService.add_comment(user, defect_id, body)
    return success(data=data, message="评论添加成功")
