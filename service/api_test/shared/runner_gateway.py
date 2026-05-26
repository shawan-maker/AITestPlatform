import copy
from datetime import datetime, timezone
from typing import Any

from ApiEngine.core import TestRunner

from service.api_test.shared.payload_builder import build_runner_case_from_payload
from service.core.enums import CaseRunStatus, CaseRunType
from service.test_environment.variable.assembler import TestEnvDataAssembler
from service.test_execution.models import ApiCaseRunRecord


def _map_run_status(result: dict[str, Any]) -> CaseRunStatus:
    status = (result.get("status") or "").lower()
    if status == "success":
        return CaseRunStatus.success
    if status == "fail":
        return CaseRunStatus.fail
    return CaseRunStatus.error


class RunnerGateway:
    @classmethod
    async def run_interface_debug(
        cls,
        *,
        interface,
        environment_id: int,
        payload: dict[str, Any] | None,
        triggered_by_id: int,
    ) -> ApiCaseRunRecord:
        test_env_data = await TestEnvDataAssembler.get_test_env_data(
            environment_id, use_snapshot=True, merge_debug=True
        )
        runner_case = build_runner_case_from_payload(interface, payload)
        env_copy = copy.deepcopy(test_env_data)
        runner = TestRunner(env_copy)
        start = datetime.now(timezone.utc)
        try:
            result = runner.execute_cases(runner_case)
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}
        end = datetime.now(timezone.utc)
        status = _map_run_status(result if isinstance(result, dict) else {})
        record = await ApiCaseRunRecord.create(
            interface_id=interface.id,
            run_type=CaseRunType.debug,
            environment_id=environment_id,
            triggered_by_id=triggered_by_id,
            case_name=runner_case.get("title") or interface.path,
            status=status,
            case_snapshot=runner_case,
            error_message=result.get("message") if isinstance(result, dict) else None,
            start_time=start,
            end_time=end,
            duration_ms=int((end - start).total_seconds() * 1000),
            api_requests_info=result if isinstance(result, dict) else None,
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
        test_env_data = await TestEnvDataAssembler.get_test_env_data(
            environment_id, use_snapshot=True, merge_debug=True
        )
        runner_case = case.case_payload
        env_copy = copy.deepcopy(test_env_data)
        runner = TestRunner(env_copy)
        start = datetime.now(timezone.utc)
        try:
            result = runner.execute_cases(runner_case)
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}
        end = datetime.now(timezone.utc)
        status = _map_run_status(result if isinstance(result, dict) else {})
        record = await ApiCaseRunRecord.create(
            api_case_id=case.id,
            interface_id=case.interface_id,
            run_type=CaseRunType.debug,
            environment_id=environment_id,
            triggered_by_id=triggered_by_id,
            case_name=case.title,
            status=status,
            case_snapshot=runner_case,
            error_message=result.get("message") if isinstance(result, dict) else None,
            start_time=start,
            end_time=end,
            duration_ms=int((end - start).total_seconds() * 1000),
            api_requests_info=result if isinstance(result, dict) else None,
        )
        case.last_run_at = end
        await case.save(update_fields=["last_run_at", "updated_at"])
        return record
