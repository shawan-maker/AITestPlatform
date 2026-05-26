from service.core.deps import require_project_editor, require_project_viewer
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


async def get_membership(project_id: int, user: User) -> ProjectMember | None:
    if user.is_super_admin:
        return None
    return await ProjectMember.get_or_none(project_id=project_id, user_id=user.id)


async def ensure_project_viewer(project_id: int, user: User) -> ProjectMember | None:
    membership = await get_membership(project_id, user)
    if user.is_super_admin:
        return None
    if membership is None:
        raise AppException("无权访问该项目", 403)
    return membership


async def ensure_project_editor(project_id: int, user: User) -> ProjectMember | None:
    membership = await ensure_project_viewer(project_id, user)
    if not is_project_editor(membership, user):
        raise AppException("需要项目编辑者及以上权限", 403)
    return membership
