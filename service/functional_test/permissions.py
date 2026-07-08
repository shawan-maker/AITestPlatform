"""功能测试模块 - permissions

权限校验
"""
from service.project.permissions import ensure_project_editor, ensure_project_viewer
from service.user.models import User


async def ensure_functional_viewer(project_id: int, user: User) -> None:
    await ensure_project_viewer(project_id, user)


async def ensure_functional_editor(project_id: int, user: User) -> None:
    await ensure_project_editor(project_id, user)


ensure_case_viewer = ensure_functional_viewer
ensure_case_editor = ensure_functional_editor
