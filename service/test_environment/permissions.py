from service.core.enums import ProjectMemberRole
from service.core.exceptions import AppException
from service.project.models import ProjectMember
from service.user.models import User


def is_project_editor(membership: ProjectMember | None, user: User) -> bool:
    if user.is_super_admin:
        return True
    if membership is None:
        return False
    return membership.role >= ProjectMemberRole.editor.value


async def get_membership(project_id: int | None, user: User) -> ProjectMember | None:
    if project_id is None:
        return None
    if user.is_super_admin:
        return None
    return await ProjectMember.get_or_none(project_id=project_id, user_id=user.id)


async def ensure_project_viewer(project_id: int, user: User) -> ProjectMember | None:
    from service.core.deps import require_project_viewer

    _, membership = await require_project_viewer(project_id, user)
    return membership


async def ensure_project_editor(project_id: int, user: User) -> ProjectMember | None:
    from service.core.deps import require_project_editor

    _, membership = await require_project_editor(project_id, user)
    return membership


async def ensure_unbound_resource_view(user: User, created_by_id: int | None) -> None:
    if user.is_super_admin:
        return
    if created_by_id != user.id:
        raise AppException("无权访问该资源", 403)


async def ensure_unbound_resource_edit(user: User, created_by_id: int | None) -> None:
    if user.is_super_admin:
        return
    if created_by_id != user.id:
        raise AppException("无权修改该资源", 403)


async def ensure_db_connection_view(conn, user: User) -> None:
    relations = await conn.environment_relations.all().prefetch_related("environment")
    if relations:
        project_ids = {rel.environment.project_id for rel in relations}
        for pid in project_ids:
            membership = await get_membership(pid, user)
            if user.is_super_admin or membership is not None:
                return
        raise AppException("无权访问该数据库连接", 403)
    await ensure_unbound_resource_view(user, conn.created_by_id)


async def ensure_db_connection_edit(conn, user: User) -> None:
    relations = await conn.environment_relations.all().prefetch_related("environment")
    if relations:
        for rel in relations:
            membership = await get_membership(rel.environment.project_id, user)
            if not is_project_editor(membership, user):
                raise AppException("需要项目编辑者及以上权限", 403)
        return
    await ensure_unbound_resource_edit(user, conn.created_by_id)


async def ensure_function_file_view(func_file, user: User) -> None:
    relations = await func_file.environment_relations.all().prefetch_related("environment")
    if relations:
        for rel in relations:
            membership = await get_membership(rel.environment.project_id, user)
            if user.is_super_admin or membership is not None:
                return
        raise AppException("无权访问该函数文件", 403)
    await ensure_unbound_resource_view(user, func_file.created_by_id)


async def ensure_function_file_edit(func_file, user: User) -> None:
    relations = await func_file.environment_relations.all().prefetch_related("environment")
    if relations:
        for rel in relations:
            membership = await get_membership(rel.environment.project_id, user)
            if not is_project_editor(membership, user):
                raise AppException("需要项目编辑者及以上权限", 403)
        return
    await ensure_unbound_resource_edit(user, func_file.created_by_id)
