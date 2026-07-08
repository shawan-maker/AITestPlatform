"""测试执行模块 - shared/summary_calculator

summary calculator
"""
from service.core.enums import CaseRunStatus, RunStatus


def compute_run_status(
    *,
    passed: int,
    failed: int,
    error: int,
    skipped: int,
    total: int,
    cancelled: bool = False,
) -> RunStatus:
    if cancelled:
        return RunStatus.cancelled
    if total <= 0:
        return RunStatus.completed
    if failed > 0 or error > 0:
        return RunStatus.failed
    if passed + skipped >= total and total > 0:
        return RunStatus.completed
    if passed + failed + error + skipped >= total and total > 0:
        return RunStatus.completed
    return RunStatus.running


def pass_rate(passed: int, planned_total: int) -> float:
    if planned_total <= 0:
        return 0.0
    return passed / planned_total


def format_pass_rate(passed: int, planned_total: int) -> str:
    if planned_total <= 0:
        return "0.0% (0/0)"
    pct = pass_rate(passed, planned_total) * 100
    return f"{pct:.1f}% ({passed}/{planned_total})"


def aggregate_case_status(statuses: list[CaseRunStatus]) -> RunStatus:
    if any(s in (CaseRunStatus.fail, CaseRunStatus.error) for s in statuses):
        return RunStatus.failed
    if statuses and all(s == CaseRunStatus.success for s in statuses):
        return RunStatus.completed
    return RunStatus.completed
