"""用户管理模块 - user_service

业务逻辑服务
"""
from datetime import datetime, timezone

from tortoise.expressions import Q

from service.core.enums import project_member_role_label
from service.core.exceptions import AppException
from service.core.redis import invalidate_user_tokens
from service.core.security import hash_password, verify_password
from service.project.models import ProjectMember
from service.user.models import User
from service.user.schemas import (
    AdminResetPasswordRequest,
    ChangeOwnPasswordRequest,
    PaginatedUsers,
    PaginatedUserLookup,
    UserBrief,
    UserCreateByAdminRequest,
    UserDetail,
    UserListQuery,
    UserLookupBrief,
    UserProjectMembership,
)


class UserService:
    @staticmethod
    def _to_user_brief(user: User) -> UserBrief:
        return UserBrief.model_validate(user)

    @staticmethod
    async def _ensure_not_last_super_admin(user: User, action: str) -> None:
        if not user.is_super_admin or user.is_deleted:
            return
        count = await User.filter(is_super_admin=True, is_deleted=False).count()
        if count <= 1:
            raise AppException(f"不能{action}最后一个超级管理员", 400)

    @staticmethod
    def _ensure_not_self(operator: User, target_id: int, action: str) -> None:
        if operator.id == target_id:
            raise AppException(f"不能对自己执行{action}操作", 400)

    @classmethod
    async def _get_active_user_or_404(cls, user_id: int) -> User:
        user = await User.get_or_none(id=user_id, is_deleted=False)
        if user is None:
            raise AppException("用户不存在或已删除", 404)
        return user

    @classmethod
    async def _build_user_detail(cls, user: User) -> UserDetail:
        memberships = await ProjectMember.filter(user_id=user.id).prefetch_related("project")
        projects = [
            UserProjectMembership(
                project_id=membership.project_id,
                project_name=membership.project.name,
                role=membership.role,
                role_label=project_member_role_label(membership.role),
            )
            for membership in memberships
        ]
        return UserDetail(
            id=user.id,
            username=user.username,
            email=user.email,
            is_super_admin=user.is_super_admin,
            is_active=user.is_active,
            is_deleted=user.is_deleted,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
            projects=projects,
        )

    @classmethod
    def _apply_list_filters(cls, query: UserListQuery):
        qs = User.all()
        if query.is_deleted is not None:
            qs = qs.filter(is_deleted=query.is_deleted)
        else:
            qs = qs.filter(is_deleted=False)
        if query.username:
            qs = qs.filter(username__icontains=query.username)
        if query.email:
            qs = qs.filter(email__icontains=query.email)
        if query.is_active is not None:
            qs = qs.filter(is_active=query.is_active)
        if query.is_super_admin is not None:
            qs = qs.filter(is_super_admin=query.is_super_admin)
        if query.project_id is not None:
            qs = qs.filter(project_memberships__project_id=query.project_id)
        if query.project_name:
            qs = qs.filter(project_memberships__project__name__icontains=query.project_name)
        return qs

    @classmethod
    async def list_users(cls, query: UserListQuery) -> PaginatedUsers:
        qs = cls._apply_list_filters(query)
        if query.project_id is not None or query.project_name:
            user_ids = await qs.distinct().values_list("id", flat=True)
            total = len(user_ids)
            offset = (query.page - 1) * query.page_size
            page_ids = user_ids[offset : offset + query.page_size]
            users = await User.filter(id__in=page_ids).order_by("-id")
        else:
            total = await qs.count()
            users = await qs.order_by("-id").offset((query.page - 1) * query.page_size).limit(
                query.page_size
            )
        return PaginatedUsers(
            total=total,
            page=query.page,
            page_size=query.page_size,
            items=[cls._to_user_brief(user) for user in users],
        )

    @classmethod
    async def lookup_users(
        cls,
        q: str | None,
        page: int,
        page_size: int,
    ) -> PaginatedUserLookup:
        qs = User.filter(is_deleted=False, is_active=True)
        if q and q.strip():
            keyword = q.strip()
            qs = qs.filter(Q(username__icontains=keyword) | Q(email__icontains=keyword))
        total = await qs.count()
        users = await qs.order_by("username").offset((page - 1) * page_size).limit(page_size)
        return PaginatedUserLookup(
            total=total,
            page=page,
            page_size=page_size,
            items=[
                UserLookupBrief(id=u.id, username=u.username, email=u.email)
                for u in users
            ],
        )

    @classmethod
    async def get_user_detail(cls, user_id: int) -> UserDetail:
        user = await User.get_or_none(id=user_id)
        if user is None:
            raise AppException("用户不存在", 404)
        return await cls._build_user_detail(user)

    @classmethod
    async def get_my_detail(cls, user: User) -> UserDetail:
        return await cls._build_user_detail(user)

    @classmethod
    async def create_user(cls, data: UserCreateByAdminRequest) -> UserBrief:
        if await User.filter(username=data.username).exists():
            raise AppException("用户名已存在", 409)
        if await User.filter(email=data.email).exists():
            raise AppException("邮箱已注册", 409)

        user = await User.create(
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
            is_super_admin=data.is_super_admin,
            is_active=data.is_active,
            is_deleted=False,
        )
        return cls._to_user_brief(user)

    @classmethod
    async def update_status(
        cls,
        user_id: int,
        is_active: bool,
        operator: User,
    ) -> UserBrief:
        user = await cls._get_active_user_or_404(user_id)
        if not is_active:
            cls._ensure_not_self(operator, user_id, "禁用")
            await cls._ensure_not_last_super_admin(user, "禁用")
        user.is_active = is_active
        await user.save(update_fields=["is_active", "updated_at"])
        if not is_active:
            await invalidate_user_tokens(user.id)
        return cls._to_user_brief(user)

    @classmethod
    async def soft_delete(cls, user_id: int, operator: User) -> None:
        user = await cls._get_active_user_or_404(user_id)
        cls._ensure_not_self(operator, user_id, "删除")
        await cls._ensure_not_last_super_admin(user, "删除")
        user.is_deleted = True
        user.is_active = False
        user.deleted_at = datetime.now(timezone.utc)
        user.deleted_by_id = operator.id
        await user.save(
            update_fields=["is_deleted", "is_active", "deleted_at", "deleted_by_id", "updated_at"]
        )
        await invalidate_user_tokens(user.id)

    @classmethod
    async def batch_delete(cls, user: User, data) -> dict:
        deleted_ids = []
        failures = []
        for item_id in data.user_ids:
            try:
                await cls.soft_delete(item_id, user)
                deleted_ids.append(item_id)
            except AppException as e:
                failures.append({'user_id': item_id, 'message': e.message})
            except Exception as e:
                failures.append({'user_id': item_id, 'message': str(e)})
        return {'deleted_ids': deleted_ids, 'failures': failures}

    @classmethod
    async def change_own_password(cls, user: User, data: ChangeOwnPasswordRequest) -> None:
        if not verify_password(data.old_password, user.password_hash):
            raise AppException("原密码不正确", 400)
        user.password_hash = hash_password(data.new_password)
        await user.save(update_fields=["password_hash", "updated_at"])
        await invalidate_user_tokens(user.id)

    @classmethod
    async def reset_password(
        cls,
        user_id: int,
        data: AdminResetPasswordRequest,
    ) -> None:
        user = await cls._get_active_user_or_404(user_id)
        user.password_hash = hash_password(data.new_password)
        await user.save(update_fields=["password_hash", "updated_at"])
        await invalidate_user_tokens(user.id)
