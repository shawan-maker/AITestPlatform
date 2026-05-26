from service.core.exceptions import AppException
from service.test_management.models import TestSuite, TestTask


async def ensure_unique_suite_name(
    project_id: int, suite_name: str, exclude_id: int | None = None
) -> None:
    qs = TestSuite.filter(project_id=project_id, suite_name=suite_name)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    if await qs.exists():
        raise AppException("套件名称在项目内已存在", 409)


async def ensure_unique_task_name(
    project_id: int, task_name: str, exclude_id: int | None = None
) -> None:
    qs = TestTask.filter(project_id=project_id, task_name=task_name)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    if await qs.exists():
        raise AppException("任务名称在项目内已存在", 409)
