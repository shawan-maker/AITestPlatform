from fastapi import APIRouter, Depends, Query

from service.core.deps import (
    get_current_active_user,
    get_current_super_admin,
    require_project_editor,
    require_project_owner_or_super_admin,
    require_project_viewer,
)
from service.core.response import success
from service.project.module_service import ModuleService
from service.project.project_service import ProjectService
from service.project.schemas import (
    ProjectCreateRequest,
    ProjectListQuery,
    ProjectMemberAddRequest,
    ProjectMemberUpdateRequest,
    ProjectModuleCreateRequest,
    ProjectModuleUpdateRequest,
    ProjectOwnerTransferRequest,
    ProjectUpdateRequest,
)
from service.user.models import User

router = APIRouter(prefix="/projects", tags=["项目"])


def get_project_list_query(
    name: str | None = Query(None, description="项目名称模糊搜索"),
    user_id: int | None = Query(None, description="按用户 ID 筛选关联项目，仅超级管理员"),
    username: str | None = Query(None, description="按用户名筛选关联项目，仅超级管理员"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ProjectListQuery:
    return ProjectListQuery(
        name=name,
        user_id=user_id,
        username=username,
        page=page,
        page_size=page_size,
    )


@router.post("", summary="创建项目")
async def create_project(
    data: ProjectCreateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await ProjectService.create_project(user, data)
    return success(data=result, message="项目创建成功")


@router.get("", summary="项目列表")
async def list_projects(
    query: ProjectListQuery = Depends(get_project_list_query),
    user: User = Depends(get_current_active_user),
):
    data = await ProjectService.list_projects(user, query)
    return success(data=data)


@router.get("/{project_id}", summary="项目详情")
async def get_project_detail(
    project_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ProjectService.get_project_detail(user, project_id)
    return success(data=data)


@router.patch("/{project_id}", summary="修改项目")
async def update_project(
    project_id: int,
    data: ProjectUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await ProjectService.update_project(user, project_id, data)
    return success(data=result, message="项目更新成功")


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
    project_id: int,
    user: User = Depends(get_current_active_user),
):
    await ProjectService.delete_project(user, project_id)
    return success(message="项目已删除")


@router.get("/{project_id}/members", summary="项目成员列表")
async def list_project_members(
    project_id: int,
    _: tuple = Depends(require_project_owner_or_super_admin),
    user: User = Depends(get_current_active_user),
):
    data = await ProjectService.list_members(user, project_id)
    return success(data=data)


@router.post("/{project_id}/members", summary="添加项目成员")
async def add_project_member(
    project_id: int,
    data: ProjectMemberAddRequest,
    user: User = Depends(get_current_active_user),
):
    result = await ProjectService.add_member(user, project_id, data)
    return success(data=result, message="成员添加成功")


@router.patch("/{project_id}/members/{user_id}", summary="修改成员角色")
async def update_project_member(
    project_id: int,
    user_id: int,
    data: ProjectMemberUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    result = await ProjectService.update_member_role(user, project_id, user_id, data)
    return success(data=result, message="成员角色更新成功")


@router.delete("/{project_id}/members/{user_id}", summary="移除项目成员")
async def remove_project_member(
    project_id: int,
    user_id: int,
    user: User = Depends(get_current_active_user),
):
    await ProjectService.remove_member(user, project_id, user_id)
    return success(message="成员已移除")


@router.put("/{project_id}/owner", summary="转移项目所有者")
async def transfer_project_owner(
    project_id: int,
    data: ProjectOwnerTransferRequest,
    super_admin: User = Depends(get_current_super_admin),
):
    result = await ProjectService.transfer_owner(super_admin, project_id, data)
    return success(data=result, message="项目所有者已转移")


@router.get("/{project_id}/modules", summary="项目模块列表")
async def list_project_modules(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: tuple = Depends(require_project_viewer),
    user: User = Depends(get_current_active_user),
):
    data = await ModuleService.list_modules(
        user, project_id, page=page, page_size=page_size
    )
    return success(data=data)


@router.post("/{project_id}/modules", summary="新增项目模块")
async def create_project_module(
    project_id: int,
    data: ProjectModuleCreateRequest,
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    result = await ModuleService.create_module(user, project_id, data)
    return success(data=result, message="模块创建成功")


@router.patch("/{project_id}/modules/{module_id}", summary="编辑项目模块")
async def update_project_module(
    project_id: int,
    module_id: int,
    data: ProjectModuleUpdateRequest,
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    result = await ModuleService.update_module(user, project_id, module_id, data)
    return success(data=result, message="模块更新成功")


@router.delete("/{project_id}/modules/{module_id}", summary="删除项目模块")
async def delete_project_module(
    project_id: int,
    module_id: int,
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    await ModuleService.delete_module(user, project_id, module_id)
    return success(message="模块已删除")
