import copy
from datetime import datetime, timezone
from typing import Any

from ApiEngine.core import TestRunner

from service.core.enums import CaseRunStatus, CaseRunType
from service.test_execution.models import ApiCaseRunRecord


def map_runner_status(result: dict[str, Any]) -> CaseRunStatus:
    status = (result.get("status") or "").lower()
    if status == "success":
        return CaseRunStatus.success
    if status == "fail":
        return CaseRunStatus.fail
    return CaseRunStatus.error


class RunnerGateway:
    @classmethod
    async def execute_case_payload(
        cls,
        *,
        test_env_data: dict[str, Any],
        case_payload: dict[str, Any],
        case_name: str,
        api_case_id: int | None = None,
        interface_id: int | None = None,
        suite_run_id: int | None = None,
        task_run_id: int | None = None,
        environment_id: int | None = None,
        env_snapshot_id: int | None = None,
        triggered_by_id: int | None = None,
        run_type: CaseRunType = CaseRunType.suite,
    ) -> ApiCaseRunRecord:
        env_copy = copy.deepcopy(test_env_data)
        runner = TestRunner(env_copy)
        start = datetime.now(timezone.utc)
        try:
            result = runner.execute_cases(case_payload)
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}
        end = datetime.now(timezone.utc)
        status = map_runner_status(result if isinstance(result, dict) else {})
        return await ApiCaseRunRecord.create(
            api_case_id=api_case_id,
            interface_id=interface_id,
            suite_run_id=suite_run_id,
            task_run_id=task_run_id,
            run_type=run_type,
            environment_id=environment_id,
            env_snapshot_id=env_snapshot_id,
            triggered_by_id=triggered_by_id,
            case_name=case_name,
            status=status,
            case_snapshot=case_payload,
            error_message=result.get("message") if isinstance(result, dict) else None,
            start_time=start,
            end_time=end,
            duration_ms=int((end - start).total_seconds() * 1000),
            api_requests_info=result if isinstance(result, dict) else None,
        )

    @classmethod
    async def run_interface_debug(
        cls,
        *,
        interface,
        environment_id: int,
        payload: dict[str, Any] | None,
        triggered_by_id: int,
    ) -> ApiCaseRunRecord:
        from service.api_test.shared.payload_builder import build_runner_case_from_payload
        from service.test_environment.variable.assembler import TestEnvDataAssembler

        test_env_data = await TestEnvDataAssembler.get_test_env_data(
            environment_id, use_snapshot=True, merge_debug=True
        )
        runner_case = build_runner_case_from_payload(interface, payload)
        record = await cls.execute_case_payload(
            test_env_data=test_env_data,
            case_payload=runner_case,
            case_name=runner_case.get("title") or interface.path,
            interface_id=interface.id,
            environment_id=environment_id,
            triggered_by_id=triggered_by_id,
            run_type=CaseRunType.debug,
        )
        interface.last_debug_environment_id = environment_id
        await interface.save(update_fields=["last_debug_environment_id", "updated_at"])
        return record

    @classmethod
    async def run_case_debug(
        cls,
        *,
        case,
        environment_id: int,
        triggered_by_id: int,
    ) -> ApiCaseRunRecord:
        from service.test_environment.variable.assembler import TestEnvDataAssembler

        test_env_data = await TestEnvDataAssembler.get_test_env_data(
            environment_id, use_snapshot=True, merge_debug=True
        )
        record = await cls.execute_case_payload(
            test_env_data=test_env_data,
            case_payload=case.case_payload,
            case_name=case.title,
            api_case_id=case.id,
            interface_id=case.interface_id,
            environment_id=environment_id,
            triggered_by_id=triggered_by_id,
            run_type=CaseRunType.debug,
        )
        case.last_run_at = record.end_time
        await case.save(update_fields=["last_run_at", "updated_at"])
        return record
