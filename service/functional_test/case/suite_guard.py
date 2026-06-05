from service.core.enums import SuiteCaseType
from service.test_management.models import SuiteCaseRelation, TaskCaseRelation, TestSuite


async def auto_remove_relations_for_cases(case_ids: list[int]) -> None:
    if not case_ids:
        return
    await SuiteCaseRelation.filter(
        case_type=SuiteCaseType.functional,
        case_id__in=case_ids,
    ).delete()
    await TaskCaseRelation.filter(
        case_type=SuiteCaseType.functional,
        case_id__in=case_ids,
    ).delete()


async def get_suite_names_for_cases(case_ids: list[int]) -> list[str]:
    """查询用例被哪些测试套件引用，返回套件名称列表。"""
    if not case_ids:
        return []
    relations = await SuiteCaseRelation.filter(
        case_type=SuiteCaseType.functional,
        case_id__in=case_ids,
    ).values_list("suite_id", flat=True)
    if not relations:
        return []
    suites = await TestSuite.filter(id__in=list(set(relations))).values_list("suite_name", flat=True)
    return list(suites)
