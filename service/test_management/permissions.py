from service.project.permissions import ensure_project_editor, ensure_project_viewer
from service.user.models import User


async def ensure_tm_viewer(project_id: int, user: User) -> None:
    await ensure_project_viewer(project_id, user)


async def ensure_tm_editor(project_id: int, user: User) -> None:
    await ensure_project_editor(project_id, user)
