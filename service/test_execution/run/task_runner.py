from datetime import datetime, timezone

from service.core.enums import RunStatus, SuiteCaseType, TaskSuiteType
from service.test_execution.models import TestSuiteRun, TestTaskRun
from service.test_execution.run.run_lock import clear_cancel_flag, is_cancel_requested
from service.test_execution.run.suite_runner import SuiteRunner
from service.test_execution.shared.summary_calculator import compute_run_status
from service.test_management.models import (
    SuiteCaseRelation,
    TaskCaseRelation,
    TaskSuiteRelation,
    TestTask,
)


class TaskRunner:
    @classmethod
    async def run_api_task(cls, task_run_id: int) -> None:
        task_run = await TestTaskRun.get(id=task_run_id).prefetch_related("task")
        task: TestTask = task_run.task
        env_id = task_run.environment_id
        snap_id = task_run.env_snapshot_id

        suite_rels = await TaskSuiteRelation.filter(task_id=task.id).order_by(
            "suite_order", "id"
        )

        total_passed = total_failed = total_error = total_skipped = 0
        cancelled = False
        start = task_run.start_time or datetime.now(timezone.utc)

        for suite_rel in suite_rels:
            if is_cancel_requested(task_run_id):
                cancelled = True
                break
            case_count = await SuiteCaseRelation.filter(
                suite_id=suite_rel.suite_id, case_type=SuiteCaseType.api
            ).count()
            suite_run = await TestSuiteRun.create(
                suite_id=suite_rel.suite_id,
                run_task_id=task_run_id,
                environment_id=env_id,
                env_snapshot_id=snap_id,
                triggered_by_id=task_run.triggered_by_id,
                status=RunStatus.running,
                total_cases=case_count,
                start_time=datetime.now(timezone.utc),
            )
            await SuiteRunner.run(
                suite_run.id,
                task_run_id=task_run_id,
                environment_id=env_id,
                env_snapshot_id=snap_id,
            )
            suite_run = await TestSuiteRun.get(id=suite_run.id)
            total_passed += suite_run.passed_cases
            total_failed += suite_run.failed_cases
            total_error += suite_run.error_cases
            total_skipped += suite_run.skipped_cases
            if suite_run.status == RunStatus.cancelled:
                cancelled = True
                break

        end = datetime.now(timezone.utc)
        total = total_passed + total_failed + total_error + total_skipped
        final_status = compute_run_status(
            passed=total_passed,
            failed=total_failed,
            error=total_error,
            skipped=total_skipped,
            total=task_run.total_cases or total,
            cancelled=cancelled,
        )
        # Don't overwrite cancelled status that was already set by CancelService
        if not cancelled:
            task_run.status = final_status
        task_run.passed_cases = total_passed
        task_run.failed_cases = total_failed
        task_run.error_cases = total_error
        task_run.skipped_cases = total_skipped
        task_run.end_time = end
        task_run.duration_ms = int((end - start).total_seconds() * 1000)
        await task_run.save()
        clear_cancel_flag(task_run_id)

    @classmethod
    async def count_task_cases(cls, task: TestTask) -> int:
        if task.type == TaskSuiteType.functional:
            return await TaskCaseRelation.filter(task_id=task.id).count()
        suite_ids = await TaskSuiteRelation.filter(task_id=task.id).values_list(
            "suite_id", flat=True
        )
        if not suite_ids:
            return 0
        return await SuiteCaseRelation.filter(
            suite_id__in=list(suite_ids), case_type=SuiteCaseType.api
        ).count()
