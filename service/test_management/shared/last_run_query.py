"""测试管理模块 - shared/last_run_query

last run query
"""
from service.core.enums import RunStatus
from service.test_execution.models import TestSuiteRun, TestTaskRun


def format_success_rate(passed: int, total: int) -> str | None:
    if total <= 0:
        return None
    pct = passed / total * 100
    return f"{pct:.1f}% ({passed}/{total})"


async def fetch_suite_last_runs(suite_ids: list[int]) -> dict[int, TestSuiteRun]:
    if not suite_ids:
        return {}
    runs = (
        await TestSuiteRun.filter(suite_id__in=suite_ids)
        .order_by("-id")
        .prefetch_related("triggered_by")
        .all()
    )
    result: dict[int, TestSuiteRun] = {}
    for run in runs:
        if run.suite_id not in result:
            result[run.suite_id] = run
    return result


async def fetch_task_last_runs(task_ids: list[int]) -> dict[int, TestTaskRun]:
    if not task_ids:
        return {}
    runs = (
        await TestTaskRun.filter(task_id__in=task_ids)
        .order_by("-id")
        .prefetch_related("triggered_by")
        .all()
    )
    result: dict[int, TestTaskRun] = {}
    for run in runs:
        if run.task_id not in result:
            result[run.task_id] = run
    return result


def _get_triggered_by_name(run) -> str | None:
    """Extract triggered_by username from a prefetched run."""
    if run is None:
        return None
    user = getattr(run, "triggered_by", None)
    if user is None:
        return None
    return getattr(user, "username", None)


def last_run_brief_from_suite_run(run: TestSuiteRun | None) -> dict:
    if run is None:
        return {
            "run_id": None,
            "status": None,
            "start_time": None,
            "end_time": None,
            "passed_cases": 0,
            "total_cases": 0,
            "success_rate": None,
            "triggered_by_name": None,
        }
    return {
        "run_id": run.id,
        "status": run.status,
        "start_time": run.start_time,
        "end_time": run.end_time,
        "passed_cases": run.passed_cases,
        "total_cases": run.total_cases,
        "success_rate": format_success_rate(run.passed_cases, run.total_cases),
        "triggered_by_name": _get_triggered_by_name(run),
    }


def last_run_brief_from_task_run(run: TestTaskRun | None) -> dict:
    if run is None:
        return {
            "run_id": None,
            "status": None,
            "start_time": None,
            "end_time": None,
            "passed_cases": 0,
            "total_cases": 0,
            "success_rate": None,
            "triggered_by_name": None,
        }
    return {
        "run_id": run.id,
        "status": run.status,
        "start_time": run.start_time,
        "end_time": run.end_time,
        "passed_cases": run.passed_cases,
        "total_cases": run.total_cases,
        "success_rate": format_success_rate(run.passed_cases, run.total_cases),
        "triggered_by_name": _get_triggered_by_name(run),
    }


def is_running_status(status: RunStatus | None) -> bool:
    return status == RunStatus.running
