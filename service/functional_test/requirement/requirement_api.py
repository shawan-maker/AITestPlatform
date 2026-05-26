from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.enums import RequirementSourceType
from service.core.response import success
from service.functional_test.requirement.requirement_service import RequirementService
from service.functional_test.requirement.schemas import (
    RequirementCreateRequest,
    RequirementListQuery,
    RequirementUpdateRequest,
)
from service.user.models import User

router = APIRouter(tags=["功能测试-需求"])


def get_requirement_list_query(
    project_id: int | None = Query(None, ge=1),
    title: str | None = Query(None),
    project_name: str | None = Query(None),
    source_type: RequirementSourceType | None = Query(None),
    module_id: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> RequirementListQuery:
    return RequirementListQuery(
        project_id=project_id,
        title=title,
        project_name=project_name,
        source_type=source_type,
        module_id=module_id,
        page=page,
        page_size=page_size,
    )


@router.get("/requirements", summary="正式需求列表")
async def list_requirements(
    query: RequirementListQuery = Depends(get_requirement_list_query),
    user: User = Depends(get_current_active_user),
):
    data = await RequirementService.list_requirements(user, query)
    return success(data=data)


@router.get("/requirements/{requirement_id}", summary="需求详情")
async def get_requirement(
    requirement_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await RequirementService.get_detail(user, requirement_id)
    return success(data=data)


@router.post("/requirements", summary="手工新增需求")
async def create_requirement(
    body: RequirementCreateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await RequirementService.create(user, body)
    return success(data=data, message="需求创建成功")


@router.patch("/requirements/{requirement_id}", summary="编辑需求")
async def update_requirement(
    requirement_id: int,
    body: RequirementUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await RequirementService.update(user, requirement_id, body)
    return success(data=data, message="需求更新成功")


@router.delete("/requirements/{requirement_id}", summary="删除需求")
async def delete_requirement(
    requirement_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await RequirementService.delete(user, requirement_id)
    return success(data=data, message="需求删除成功")
