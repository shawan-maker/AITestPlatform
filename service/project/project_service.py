import asyncio

from tortoise.transactions import in_transaction

from service.ai_generation.models import AIGenerationSession
from service.api_test.interface.models import ApiInterfaceCatalog
from service.api_test.models import ApiBaseCase, ApiInterface, ApiTestCase
from service.core.enums import ProjectMemberRole, project_member_role_label
from service.core.exceptions import AppException
from service.functional_test.models import FunctionalCase, RequirementDoc
from service.knowledge.models import KnowledgeDocument, KnowledgeWorkspace
from service.project.models import Project, ProjectMember
from service.project.schemas import (
    PaginatedProjects,
    ProjectBrief,
    ProjectCreateRequest,
    ProjectDetail,
    ProjectListQuery,
    ProjectMemberAddRequest,
    ProjectMemberOut,
    ProjectMemberUpdateRequest,
    ProjectOwnerTransferRequest,
    ProjectUpdateRequest,
)
from service.test_environment.models import TestEnvironment
from service.test_management.models import TestSuite, TestTask
from service.user.models import User

BLOCKER_MODELS: list[tuple[type, str]] = [
    (TestEnvironment, "environments"),
    (KnowledgeWorkspace, "knowledge_workspaces"),
    (KnowledgeDocument, "knowledge_documents"),
    (RequirementDoc, "requirement_docs"),
    (FunctionalCase, "functional_cases"),
    (ApiInterfaceCatalog, "api_interface_catalogs"),
    (ApiInterface, "api_interfaces"),
    (ApiBaseCase, "api_base_cases"),
    (ApiTestCase, "api_test_cases"),
    (TestTask, "test_tasks"),
    (TestSuite, "test_suites"),
    (AIGenerationSession, "ai_generation_sessions"),
]


class ProjectService:
    @staticmethod
    def _normalize_name(name: str) -> str:
        stripped = name.strip()
        if not stripped:
            raise AppException("项目名称不能为空", 400)
        return stripped

    @classmethod
    async def _ensure_unique_name(cls, name: str, exclude_id: int | None = None) -> None:
        qs = Project.filter(name=name)
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if await qs.exists():
            raise AppException("项目名称已存在", 409)

    @classmethod
    async def _get_addable_user(cls, user_id: int) -> User:
        user = await User.get_or_none(id=user_id, is_deleted=False)
        if user is None:
            raise AppException("用户不存在或已删除", 404)
        if not user.is_active:
            raise AppException("不能添加已禁用的用户", 400)
        return user

    @classmethod
    async def _get_membership(
        cls,
        project_id: int,
        user_id: int,
    ) -> ProjectMember | None:
        return await ProjectMember.get_or_none(
            project_id=project_id,
            user_id=user_id,
        )

    @classmethod
    def _can_view_members(cls, user: User, membership: ProjectMember | None) -> bool:
        if user.is_super_admin:
            return True
        return membership is not None and membership.role == ProjectMemberRole.owner.value

    @classmethod
    async def _build_project_brief(
        cls,
        project: Project,
        current_user: User,
        membership: ProjectMember | None,
    ) -> ProjectBrief:
        if not hasattr(project, "owner") or project.owner is None:
            await project.fetch_related("owner")
        is_member = membership is not None
        my_role = membership.role if membership else None
        return ProjectBrief(
            id=project.id,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            owner_username=project.owner.username,
            my_role=my_role,
            my_role_label=project_member_role_label(my_role) if my_role is not None else None,
            is_member=is_member,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    @classmethod
    async def _build_members_out(cls, project_id: int) -> list[ProjectMemberOut]:
        members = (
            await ProjectMember.filter(project_id=project_id)
            .prefetch_related("user")
            .order_by("created_at")
        )
        return [
            ProjectMemberOut(
                user_id=member.user_id,
                username=member.user.username,
                email=member.user.email,
                role=member.role,
                role_label=project_member_role_label(member.role),
                joined_at=member.created_at,
            )
            for member in members
        ]

    @classmethod
    async def _build_project_detail(
        cls,
        project: Project,
        current_user: User,
        membership: ProjectMember | None,
    ) -> ProjectDetail:
        brief = await cls._build_project_brief(project, current_user, membership)
        members = None
        if cls._can_view_members(current_user, membership):
            members = await cls._build_members_out(project.id)
        return ProjectDetail(**brief.model_dump(), members=members)

    @classmethod
    async def _check_delete_blockers(cls, project_id: int) -> dict[str, int]:
        async def count_blocker(model: type, key: str) -> tuple[str, int]:
            count = await model.filter(project_id=project_id).count()
            return key, count

        results = await asyncio.gather(
            *[count_blocker(model, key) for model, key in BLOCKER_MODELS]
        )
        return {key: count for key, count in results if count > 0}

    @classmethod
    async def create_project(cls, creator: User, data: ProjectCreateRequest) -> ProjectDetail:
        name = cls._normalize_name(data.name)
        await cls._ensure_unique_name(name)

        async with in_transaction():
            project = await Project.create(
                name=name,
                description=data.description,
                owner_id=creator.id,
            )
            await ProjectMember.create(
                project=project,
                user=creator,
                role=ProjectMemberRole.owner.value,
                granted_by=creator,
            )

        await project.fetch_related("owner")
        membership = await cls._get_membership(project.id, creator.id)
        return await cls._build_project_detail(project, creator, membership)

    @classmethod
    async def list_projects(cls, current_user: User, query: ProjectListQuery) -> PaginatedProjects:
        if (query.user_id or query.username) and not current_user.is_super_admin:
            raise AppException("需要超级管理员权限", 403)

        if current_user.is_super_admin:
            qs = Project.all()
            if query.user_id is not None:
                qs = qs.filter(members__user_id=query.user_id)
            elif query.username:
                target_user = await User.get_or_none(username=query.username, is_deleted=False)
                if target_user is None:
                    return PaginatedProjects(
                        total=0,
                        page=query.page,
                        page_size=query.page_size,
                        items=[],
                    )
                qs = qs.filter(members__user_id=target_user.id)
        else:
            qs = Project.filter(members__user_id=current_user.id)

        if query.name:
            qs = qs.filter(name__icontains=query.name)

        qs = qs.distinct().prefetch_related("owner").order_by("-created_at")
        total = await qs.count()
        projects = await qs.offset((query.page - 1) * query.page_size).limit(query.page_size)

        items: list[ProjectBrief] = []
        for project in projects:
            membership = await cls._get_membership(project.id, current_user.id)
            items.append(await cls._build_project_brief(project, current_user, membership))

        return PaginatedProjects(
            total=total,
            page=query.page,
            page_size=query.page_size,
            items=items,
        )

    @classmethod
    async def get_project_detail(
        cls,
        current_user: User,
        project_id: int,
    ) -> ProjectDetail:
        project = await Project.get_or_none(id=project_id).prefetch_related("owner")
        if project is None:
            raise AppException("项目不存在", 404)

        membership = None
        if not current_user.is_super_admin:
            membership = await cls._get_membership(project_id, current_user.id)
            if membership is None:
                raise AppException("无权访问该项目", 403)

        return await cls._build_project_detail(project, current_user, membership)

    @classmethod
    async def update_project(
        cls,
        operator: User,
        project_id: int,
        data: ProjectUpdateRequest,
    ) -> ProjectDetail:
        project, _ = await cls._require_owner_or_super_admin(project_id, operator)

        update_fields: list[str] = []
        if data.name is not None:
            name = cls._normalize_name(data.name)
            if name != project.name:
                await cls._ensure_unique_name(name, exclude_id=project.id)
                project.name = name
                update_fields.append("name")
        if data.description is not None:
            project.description = data.description
            update_fields.append("description")

        if update_fields:
            update_fields.append("updated_at")
            await project.save(update_fields=update_fields)

        membership = await cls._get_membership(project_id, operator.id)
        return await cls._build_project_detail(project, operator, membership)

    @classmethod
    async def delete_project(cls, operator: User, project_id: int) -> None:
        project, _ = await cls._require_owner_or_super_admin(project_id, operator)
        blockers = await cls._check_delete_blockers(project.id)
        if blockers:
            raise AppException("请先清理子资源", 409, data={"blockers": blockers})
        # TODO: Phase2 异步清理 rag/rag_storage/{workspace_key}/ 物理目录
        await project.delete()

    @classmethod
    async def list_members(cls, operator: User, project_id: int) -> list[ProjectMemberOut]:
        project, _ = await cls._require_owner_or_super_admin(project_id, operator)
        return await cls._build_members_out(project.id)

    @classmethod
    async def add_member(
        cls,
        operator: User,
        project_id: int,
        data: ProjectMemberAddRequest,
    ) -> ProjectMemberOut:
        project, _ = await cls._require_owner_or_super_admin(project_id, operator)
        target_user = await cls._get_addable_user(data.user_id)

        if await ProjectMember.filter(project_id=project.id, user_id=target_user.id).exists():
            raise AppException("用户已是项目成员", 409)

        member = await ProjectMember.create(
            project=project,
            user=target_user,
            role=data.role,
            granted_by=operator,
        )
        await member.fetch_related("user")
        return ProjectMemberOut(
            user_id=member.user_id,
            username=member.user.username,
            email=member.user.email,
            role=member.role,
            role_label=project_member_role_label(member.role),
            joined_at=member.created_at,
        )

    @classmethod
    async def update_member_role(
        cls,
        operator: User,
        project_id: int,
        user_id: int,
        data: ProjectMemberUpdateRequest,
    ) -> ProjectMemberOut:
        project, _ = await cls._require_owner_or_super_admin(project_id, operator)
        member = await ProjectMember.get_or_none(project_id=project.id, user_id=user_id)
        if member is None:
            raise AppException("成员不存在", 404)
        if member.role == ProjectMemberRole.owner.value:
            raise AppException("不能修改项目所有者的角色", 400)

        member.role = data.role
        member.granted_by = operator
        await member.save(update_fields=["role", "granted_by_id", "updated_at"])
        await member.fetch_related("user")
        return ProjectMemberOut(
            user_id=member.user_id,
            username=member.user.username,
            email=member.user.email,
            role=member.role,
            role_label=project_member_role_label(member.role),
            joined_at=member.created_at,
        )

    @classmethod
    async def remove_member(
        cls,
        operator: User,
        project_id: int,
        user_id: int,
    ) -> None:
        project, _ = await cls._require_owner_or_super_admin(project_id, operator)
        member = await ProjectMember.get_or_none(project_id=project.id, user_id=user_id)
        if member is None:
            raise AppException("成员不存在", 404)
        if member.role == ProjectMemberRole.owner.value:
            raise AppException("不能移除项目所有者", 400)
        if operator.id == user_id and member.role == ProjectMemberRole.owner.value:
            raise AppException("不能移除自己", 400)
        await member.delete()

    @classmethod
    async def transfer_owner(
        cls,
        super_admin: User,
        project_id: int,
        data: ProjectOwnerTransferRequest,
    ) -> ProjectDetail:
        project = await Project.get_or_none(id=project_id).prefetch_related("owner")
        if project is None:
            raise AppException("项目不存在", 404)

        if project.owner_id == data.new_owner_user_id:
            raise AppException("该用户已是项目所有者", 400)

        new_user = await cls._get_addable_user(data.new_owner_user_id)

        async with in_transaction():
            old_owner_member = await ProjectMember.get_or_none(
                project_id=project.id,
                role=ProjectMemberRole.owner.value,
            )
            if old_owner_member is None:
                raise AppException("项目缺少有效的所有者成员记录", 400)

            new_member = await ProjectMember.get_or_none(
                project_id=project.id,
                user_id=new_user.id,
            )
            if new_member is None:
                new_member = await ProjectMember.create(
                    project=project,
                    user=new_user,
                    role=ProjectMemberRole.owner.value,
                    granted_by=super_admin,
                )
            else:
                new_member.role = ProjectMemberRole.owner.value
                new_member.granted_by = super_admin
                await new_member.save(update_fields=["role", "granted_by_id", "updated_at"])

            old_owner_member.role = ProjectMemberRole.editor.value
            old_owner_member.granted_by = super_admin
            await old_owner_member.save(update_fields=["role", "granted_by_id", "updated_at"])

            project.owner_id = new_user.id
            await project.save(update_fields=["owner_id", "updated_at"])

        await project.fetch_related("owner")
        membership = await cls._get_membership(project.id, super_admin.id)
        return await cls._build_project_detail(project, super_admin, membership)

    @classmethod
    async def _require_owner_or_super_admin(
        cls,
        project_id: int,
        user: User,
    ) -> tuple[Project, User]:
        project = await Project.get_or_none(id=project_id).prefetch_related("owner")
        if project is None:
            raise AppException("项目不存在", 404)
        if user.is_super_admin:
            return project, user
        membership = await ProjectMember.get_or_none(
            project_id=project_id,
            user_id=user.id,
            role=ProjectMemberRole.owner.value,
        )
        if membership is None:
            raise AppException("需要项目所有者或超级管理员权限", 403)
        return project, user
