from service.core.enums import SuiteCaseType
from service.test_management.models import TaskCaseRelation


async def remove_task_case_relations_for_cases(case_ids: list[int]) -> None:
    if not case_ids:
        return
    await TaskCaseRelation.filter(
        case_type=SuiteCaseType.functional,
        case_id__in=case_ids,
    ).delete()
