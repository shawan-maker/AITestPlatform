import copy

from service.api_test.dependency.resolver_service import DependencyResolverService
from service.api_test.models import ApiTestCase
from service.api_test.shared.runner_gateway import RunnerGateway
from service.core.enums import CaseRunStatus, CaseRunType, ExecStatus
from service.test_execution.case_prepare_service import prepare_case_payload
from service.test_execution.models import ApiCaseRunRecord
from service.test_execution.shared.run_var_context import RunVarContext


class SuiteCaseRunner:
    @classmethod
    async def run_one(
        cls,
        *,
        case: ApiTestCase,
        project_id: int,
        test_env_data: dict,
        use_dependency: bool,
        suite_run_id: int,
        task_run_id: int | None,
        environment_id: int,
        env_snapshot_id: int,
        triggered_by_id: int,
        run_context: RunVarContext | None = None,
    ) -> ApiCaseRunRecord:
        ctx = run_context or RunVarContext()
        env_data = copy.deepcopy(test_env_data)
        if use_dependency and case.interface_id:
            resolved = await DependencyResolverService.resolve(case.interface_id)
            for dep_api in resolved.ordered_to_apis:
                dep_cases = await ApiTestCase.filter(
                    interface_id=dep_api.id,
                    case_kind="precondition",
                    exec_status=ExecStatus.ready,
                ).order_by("sort_order", "id")
                for dep_case in dep_cases:
                    prepared = await prepare_case_payload(project_id, dep_case.case_payload)
                    record = await RunnerGateway.execute_case_payload(
                        test_env_data=env_data,
                        case_payload=prepared,
                        case_name=dep_case.title,
                        api_case_id=dep_case.id,
                        interface_id=dep_api.id,
                        suite_run_id=suite_run_id,
                        task_run_id=task_run_id,
                        environment_id=environment_id,
                        env_snapshot_id=env_snapshot_id,
                        triggered_by_id=triggered_by_id,
                        run_type=CaseRunType.suite,
                        project_id=project_id,
                        temp_vars=ctx.temp_vars,
                    )
                    if record.status != CaseRunStatus.success:
                        return record
        prepared_main = await prepare_case_payload(project_id, case.case_payload)
        return await RunnerGateway.execute_case_payload(
            test_env_data=env_data,
            case_payload=prepared_main,
            case_name=case.title,
            api_case_id=case.id,
            interface_id=case.interface_id,
            suite_run_id=suite_run_id,
            task_run_id=task_run_id,
            environment_id=environment_id,
            env_snapshot_id=env_snapshot_id,
            triggered_by_id=triggered_by_id,
            run_type=CaseRunType.suite,
            project_id=project_id,
            temp_vars=ctx.temp_vars,
        )
