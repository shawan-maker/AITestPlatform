from service.core.enums import SuiteCaseType
from service.test_management.models import SuiteCaseRelation, TaskCaseRelation


async def remove_suite_relations_for_cases(case_ids: list[int]) -> None:
    if not case_ids:
        return
    await SuiteCaseRelation.filter(
        case_type=SuiteCaseType.api,
        case_id__in=case_ids,
    ).delete()
    await TaskCaseRelation.filter(
        case_type=SuiteCaseType.functional,
        case_id__in=case_ids,
    ).delete()
