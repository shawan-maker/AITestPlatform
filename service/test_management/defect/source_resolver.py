from service.core.enums import DefectSourceType
from service.test_execution.models import (
    ApiCaseRunRecord,
    FunctionalCaseRunRecord,
    TestDefect,
    TestSuiteRun,
    TestTaskRun,
)


class DefectSourceBrief:
    def __init__(
        self,
        *,
        source_type: DefectSourceType,
        source_run_id: int | None,
        source_case_id: int | None,
        case_name: str | None = None,
        run_label: str | None = None,
        source_unreachable: bool = False,
    ) -> None:
        self.source_type = source_type
        self.source_run_id = source_run_id
        self.source_case_id = source_case_id
        self.case_name = case_name
        self.run_label = run_label
        self.source_unreachable = source_unreachable


async def resolve_source_brief(defect: TestDefect) -> DefectSourceBrief:
    if defect.source_type == DefectSourceType.manual:
        return DefectSourceBrief(
            source_type=defect.source_type,
            source_run_id=None,
            source_case_id=None,
        )

    case_name: str | None = None
    run_label: str | None = None
    unreachable = False

    if defect.source_type == DefectSourceType.api_case and defect.source_case_id:
        from service.api_test.models import ApiTestCase

        case = await ApiTestCase.get_or_none(id=defect.source_case_id)
        if case:
            case_name = case.title
            if case.project_id != defect.project_id:
                unreachable = True

    if defect.source_type == DefectSourceType.functional_case and defect.source_case_id:
        from service.functional_test.case.models import FunctionalCase

        case = await FunctionalCase.get_or_none(id=defect.source_case_id)
        if case:
            case_name = case.case_name
            if case.project_id != defect.project_id:
                unreachable = True

    if defect.source_run_id:
        suite_run = await TestSuiteRun.get_or_none(id=defect.source_run_id)
        if suite_run:
            run_label = f"套件执行 #{suite_run.id}"
            await suite_run.fetch_related("suite")
            if suite_run.suite and suite_run.suite.project_id != defect.project_id:
                unreachable = True
        else:
            task_run = await TestTaskRun.get_or_none(id=defect.source_run_id)
            if task_run:
                run_label = f"任务执行 #{task_run.id}"
                await task_run.fetch_related("task")
                if task_run.task and task_run.task.project_id != defect.project_id:
                    unreachable = True

    if not case_name and defect.source_case_id:
        record = await ApiCaseRunRecord.filter(
            defect_id=defect.id, api_case_id=defect.source_case_id
        ).first()
        if record:
            case_name = record.case_name
        else:
            frecord = await FunctionalCaseRunRecord.filter(
                defect_id=defect.id, functional_case_id=defect.source_case_id
            ).first()
            if frecord:
                await frecord.fetch_related("functional_case")
                if frecord.functional_case:
                    case_name = frecord.functional_case.case_name

    return DefectSourceBrief(
        source_type=defect.source_type,
        source_run_id=defect.source_run_id,
        source_case_id=defect.source_case_id,
        case_name=case_name,
        run_label=run_label,
        source_unreachable=unreachable,
    )
