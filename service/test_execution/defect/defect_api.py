"""测试执行模块 - defect/defect_api

API 路由端点
"""
from fastapi import APIRouter, Depends

from service.core.deps import get_current_active_user
from service.core.response import success
from service.test_execution.defect.defect_service import DefectService
from service.test_execution.defect.schemas import DefectBatchLinkRequest, DefectCreateRequest
from service.user.models import User

router = APIRouter(prefix="/defects", tags=["测试执行-缺陷"])


@router.post("", summary="创建缺陷并关联运行记录")
async def create_defect(
    body: DefectCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DefectService.create(user, body)
    return success(data=data, message="缺陷创建成功")


@router.post("/batch-link", summary="批量关联缺陷")
async def batch_link_defects(
    body: DefectBatchLinkRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DefectService.batch_link(user, body)
    return success(data=data, message="缺陷关联成功")
