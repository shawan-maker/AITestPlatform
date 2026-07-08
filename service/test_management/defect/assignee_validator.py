"""测试管理模块 - defect/assignee_validator

assignee validator
"""
from service.core.exceptions import AppException
from service.project.models import ProjectMember
from service.user.models import User


async def ensure_assignee_in_project(
    project_id: int,
    assignee_id: int | None,
    *,
    operator: User,
) -> None:
    if assignee_id is None:
        return
    if assignee_id == operator.id and operator.is_super_admin:
        return
    assignee = await User.get_or_none(id=assignee_id, is_active=True, is_deleted=False)
    if assignee is None:
        raise AppException("处理人用户不存在或已禁用", 404)
    if assignee.is_super_admin:
        return
    is_member = await ProjectMember.filter(
        project_id=project_id,
        user_id=assignee_id,
        status=1,
    ).exists()
    if not is_member:
        raise AppException("处理人须为项目成员", 400)
