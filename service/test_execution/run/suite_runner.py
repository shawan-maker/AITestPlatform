import asyncio
from datetime import datetime, timezone

from service.api_test.models import ApiTestCase
from service.core.enums import CaseRunStatus, RunMode, RunStatus, SuiteCaseType
from service.test_environment.variable.assembler import TestEnvDataAssembler
from service.test_execution.models import TestSuiteRun
from service.test_execution.run.run_lock import clear_cancel_flag, is_cancel_requested
from service.test_execution.run.suite_case_runner import SuiteCaseRunner
from service.test_execution.shared.run_var_context import RunVarContext
from service.test_execution.shared.summary_calculator import compute_run_status
from service.test_management.models import SuiteCaseRelation, TestSuite


class SuiteRunner:
    @classmethod
    async def run(
        cls,
        suite_run_id: int,
        *,
        task_run_id: int | None = None,
        environment_id: int | None = None,
        env_snapshot_id: int | None = None,
    ) -> None:
        suite_run = await TestSuiteRun.get(id=suite_run_id).prefetch_related("suite")
        suite: TestSuite = suite_run.suite
        env_id = environment_id or suite_run.environment_id
        snap_id = env_snapshot_id or suite_run.env_snapshot_id
        test_env_data = await TestEnvDataAssembler.assemble(env_id)
        if snap_id:
            snap_payload = await TestEnvDataAssembler.get_snapshot_payload_by_id(snap_id)
            if snap_payload:
                test_env_data = snap_payload

        relations = await SuiteCaseRelation.filter(
            suite_id=suite.id, case_type=SuiteCaseType.api
        ).order_by("case_order", "id")

        passed = failed = error = skipped = 0
        cancelled = False
        start = suite_run.start_time or datetime.now(timezone.utc)
        serial_context = RunVarContext()

        async def run_relation(
            rel: SuiteCaseRelation,
            run_context: RunVarContext,
        ) -> tuple[bool, CaseRunStatus | None]:
            case = await ApiTestCase.get_or_none(id=rel.case_id)
            if case is None:
                return True, None
            record = await SuiteCaseRunner.run_one(
                case=case,
                project_id=suite.project_id,
                test_env_data=test_env_data,
                use_dependency=rel.use_dependency,
                suite_run_id=suite_run_id,
                task_run_id=task_run_id,
                environment_id=env_id,
                env_snapshot_id=snap_id,
                triggered_by_id=suite_run.triggered_by_id,
                run_context=run_context,
            )
            return False, record.status

        def apply_result(was_skipped: bool, status: CaseRunStatus | None) -> None:
            nonlocal passed, failed, error, skipped
            if was_skipped:
                skipped += 1
            elif status == CaseRunStatus.success:
                passed += 1
            elif status == CaseRunStatus.fail:
                failed += 1
            else:
                error += 1

        async def flush_progress() -> None:
            """将当前进度增量写入 DB，供列表页实时刷新。"""
            suite_run.passed_cases = passed
            suite_run.failed_cases = failed
            suite_run.error_cases = error
            suite_run.skipped_cases = skipped
            await suite_run.save(
                update_fields=["passed_cases", "failed_cases", "error_cases", "skipped_cases", "updated_at"]
            )

        dep_serial: list[SuiteCaseRelation] = []
        parallel_main: list[SuiteCaseRelation] = []
        for rel in relations:
            if rel.use_dependency:
                dep_serial.append(rel)
            else:
                parallel_main.append(rel)

        if suite.run_mode == RunMode.parallel:
            for rel in dep_serial:
                if is_cancel_requested(suite_run_id):
                    cancelled = True
                    break
                apply_result(*await run_relation(rel, serial_context))
                await flush_progress()

            if not cancelled and parallel_main:
                if is_cancel_requested(suite_run_id):
                    cancelled = True
                else:

                    async def run_parallel(rel: SuiteCaseRelation) -> tuple[bool, CaseRunStatus | None]:
                        return await run_relation(rel, RunVarContext())

                    results = await asyncio.gather(*(run_parallel(r) for r in parallel_main))
                    for was_skipped, status in results:
                        apply_result(was_skipped, status)
                    await flush_progress()
        else:
            for rel in relations:
                if is_cancel_requested(suite_run_id):
                    cancelled = True
                    break
                apply_result(*await run_relation(rel, serial_context))
                await flush_progress()

        end = datetime.now(timezone.utc)
        total = passed + failed + error + skipped
        final_status = compute_run_status(
            passed=passed,
            failed=failed,
            error=error,
            skipped=skipped,
            total=suite_run.total_cases or total,
            cancelled=cancelled,
        )
        # Don't overwrite cancelled status that was already set by CancelService
        await TestSuiteRun.filter(id=suite_run_id).exclude(status=RunStatus.cancelled).update(
            status=final_status,
            passed_cases=passed,
            failed_cases=failed,
            error_cases=error,
            skipped_cases=skipped,
            end_time=end,
            duration_ms=int((end - start).total_seconds() * 1000),
        )
        # For cancelled runs, only update progress counts and timing
        if cancelled:
            await TestSuiteRun.filter(id=suite_run_id).update(
                passed_cases=passed,
                failed_cases=failed,
                error_cases=error,
                skipped_cases=skipped,
                end_time=end,
                duration_ms=int((end - start).total_seconds() * 1000),
            )
        clear_cancel_flag(suite_run_id)
