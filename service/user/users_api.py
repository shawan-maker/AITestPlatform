"""用户管理模块 - users_api

API 路由端点
"""
from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user, get_current_super_admin
from service.core.response import success
from service.user.models import User
from service.user.schemas import (
    AdminResetPasswordRequest,
    ChangeOwnPasswordRequest,
    UserBatchDeleteRequest,
    UserCreateByAdminRequest,
    UserListQuery,
    UserStatusUpdateRequest,
)
from service.user.user_service import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])


def get_user_list_query(
    username: str | None = Query(None, description="用户名模糊搜索"),
    email: str | None = Query(None, description="邮箱模糊搜索"),
    project_name: str | None = Query(None, description="关联项目名称模糊搜索"),
    project_id: int | None = Query(None, description="关联项目 ID"),
    is_active: bool | None = Query(None, description="激活状态"),
    is_super_admin: bool | None = Query(None, description="是否超级管理员"),
    is_deleted: bool | None = Query(None, description="是否已软删除，默认 false"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> UserListQuery:
    return UserListQuery(
        username=username,
        email=email,
        project_name=project_name,
        project_id=project_id,
        is_active=is_active,
        is_super_admin=is_super_admin,
        is_deleted=is_deleted,
        page=page,
        page_size=page_size,
    )


@router.get("/me", summary="当前用户详情")
async def get_my_detail(user: User = Depends(get_current_active_user)):
    data = await UserService.get_my_detail(user)
    return success(data=data)


@router.get("", summary="用户列表与搜索")
async def list_users(
    query: UserListQuery = Depends(get_user_list_query),
    _: User = Depends(get_current_super_admin),
):
    data = await UserService.list_users(query)
    return success(data=data)


@router.get("/lookup", summary="用户模糊搜索（添加成员等）")
async def lookup_users(
    q: str | None = Query(None, description="用户名或邮箱模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    _: User = Depends(get_current_active_user),
):
    data = await UserService.lookup_users(q, page, page_size)
    return success(data=data)


@router.post("/batch-delete", summary="批量删除用户")
async def batch_delete(
    data: UserBatchDeleteRequest,
    user: User = Depends(get_current_super_admin),
):
    result = await UserService.batch_delete(user, data)
    return success(data=result)


@router.get("/{user_id}", summary="用户详情")
async def get_user_detail(
    user_id: int,
    _: User = Depends(get_current_super_admin),
):
    data = await UserService.get_user_detail(user_id)
    return success(data=data)


@router.post("", summary="管理员创建用户")
async def create_user(
    data: UserCreateByAdminRequest,
    _: User = Depends(get_current_super_admin),
):
    user = await UserService.create_user(data)
    return success(data=user, message="用户创建成功")


@router.patch("/{user_id}/status", summary="激活/去激活用户")
async def update_user_status(
    user_id: int,
    data: UserStatusUpdateRequest,
    operator: User = Depends(get_current_super_admin),
):
    user = await UserService.update_status(user_id, data.is_active, operator)
    message = "用户已激活" if data.is_active else "用户已去激活"
    return success(data=user, message=message)


@router.delete("/{user_id}", summary="软删除用户")
async def soft_delete_user(
    user_id: int,
    operator: User = Depends(get_current_super_admin),
):
    await UserService.soft_delete(user_id, operator)
    return success(message="用户已删除")


@router.put("/me/password", summary="修改当前用户密码")
async def change_own_password(
    data: ChangeOwnPasswordRequest,
    user: User = Depends(get_current_active_user),
):
    await UserService.change_own_password(user, data)
    return success(message="密码修改成功，请重新登录")


@router.put("/{user_id}/password", summary="管理员重置用户密码")
async def reset_user_password(
    user_id: int,
    data: AdminResetPasswordRequest,
    _: User = Depends(get_current_super_admin),
):
    await UserService.reset_password(user_id, data)
    return success(message="密码重置成功")
