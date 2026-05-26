from service.core.enums import SuiteCaseType
from service.functional_test.case.models import FunctionalCase
from service.test_management.models import SuiteCaseRelation, TestSuite


async def get_blocking_suite_names(case_id: int) -> list[str]:
    relations = await SuiteCaseRelation.filter(
        case_type=SuiteCaseType.functional,
        case_id=case_id,
    ).prefetch_related("suite")
    names: list[str] = []
    seen: set[int] = set()
    for rel in relations:
        if rel.suite_id in seen:
            continue
        seen.add(rel.suite_id)
        names.append(rel.suite.suite_name)
    return names


async def assert_case_deletable(case_id: int) -> list[str]:
    return await get_blocking_suite_names(case_id)


async def assert_cases_deletable(case_ids: list[int]) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for case_id in case_ids:
        names = await get_blocking_suite_names(case_id)
        if names:
            result[case_id] = names
    return result
