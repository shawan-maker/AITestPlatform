import copy

from service.api_test.models import ApiTestCase
from service.api_test.shared.runner_gateway import RunnerGateway
from service.core.enums import CaseRunStatus, CaseRunType
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

        # 按 precondition_ids 加载关联的前置用例
        pre_cases = []
        if use_dependency:
            pre_ids = (case.case_payload or {}).get("precondition_ids") or []
            if pre_ids:
                pre_cases = await ApiTestCase.filter(
                    id__in=pre_ids,
                ).order_by("sort_order", "id")

        # 构建主用例 payload，嵌入前置用例（合并为一次引擎调用）
        prepared_main = await prepare_case_payload(project_id, case.case_payload)
        if pre_cases:
            engine_preconditions = []
            for pc in pre_cases:
                prepared_pc = await prepare_case_payload(project_id, pc.case_payload)
                engine_preconditions.append(prepared_pc)
            prepared_main["preconditions"] = engine_preconditions

        record = await RunnerGateway.execute_case_payload(
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

        # 从日志解析前置步骤结果，更新各 DB 前置用例
        if pre_cases:
            await RunnerGateway._update_precondition_results(pre_cases, record)

        return record
