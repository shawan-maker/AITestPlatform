from service.core.enums import SuiteCaseType
from service.test_management.models import (
    SuiteCaseRelation,
    TaskCaseRelation,
    TaskSuiteRelation,
)


async def count_suite_cases(suite_ids: list[int]) -> dict[int, int]:
    if not suite_ids:
        return {}
    rows = await SuiteCaseRelation.filter(suite_id__in=suite_ids).values("suite_id")
    counts: dict[int, int] = {}
    for row in rows:
        sid = row["suite_id"]
        counts[sid] = counts.get(sid, 0) + 1
    return counts


async def count_task_api_cases(task_ids: list[int]) -> dict[int, int]:
    """API/UI 任务：关联套件内用例数之和（不去重）。"""
    if not task_ids:
        return {}
    relations = await TaskSuiteRelation.filter(task_id__in=task_ids).values(
        "task_id", "suite_id"
    )
    task_suite_map: dict[int, list[int]] = {}
    suite_ids: set[int] = set()
    for row in relations:
        task_suite_map.setdefault(row["task_id"], []).append(row["suite_id"])
        suite_ids.add(row["suite_id"])
    suite_counts = await count_suite_cases(list(suite_ids))
    result: dict[int, int] = {}
    for task_id, sids in task_suite_map.items():
        result[task_id] = sum(suite_counts.get(sid, 0) for sid in sids)
    return result


async def count_task_functional_cases(task_ids: list[int]) -> dict[int, int]:
    if not task_ids:
        return {}
    rows = await TaskCaseRelation.filter(
        task_id__in=task_ids, case_type=SuiteCaseType.functional
    ).values("task_id")
    counts: dict[int, int] = {}
    for row in rows:
        tid = row["task_id"]
        counts[tid] = counts.get(tid, 0) + 1
    return counts
