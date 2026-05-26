from service.core.enums import CaseRunStatus, DefectSeverity, RunStatus
from service.core.exceptions import AppException
from service.test_execution.models import ApiCaseRunRecord, TestDefect, TestSuiteRun, TestTaskRun
from service.test_execution.report.schemas import (
    CaseRunDetailOut,
    CaseRunLogOut,
    DefectSeverityChart,
    ReportSummaryOut,
    SuiteReportOut,
    SuiteReportSection,
    TaskReportOut,
)
from service.test_execution.shared.summary_calculator import format_pass_rate, pass_rate
from service.test_management.permissions import ensure_tm_viewer
from service.test_management.models import TestSuite, TestTask
from service.user.models import User


class ReportService:
    @classmethod
    def _build_summary_from_counters(
        cls,
        *,
        total: int,
        passed: int,
        failed: int,
        error: int,
        skipped: int,
        status: RunStatus,
        start_time,
        end_time,
        duration_ms,
    ) -> ReportSummaryOut:
        return ReportSummaryOut(
            total=total,
            passed=passed,
            failed=failed,
            error=error,
            skipped=skipped,
            pass_rate=pass_rate(passed, total),
            pass_rate_display=format_pass_rate(passed, total),
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
        )

    @classmethod
    async def _defect_chart_for_run(cls, run_id: int, *, is_task: bool) -> list[DefectSeverityChart]:
        if is_task:
            records = await ApiCaseRunRecord.filter(task_run_id=run_id).values_list(
                "defect_id", flat=True
            )
        else:
            records = await ApiCaseRunRecord.filter(suite_run_id=run_id).values_list(
                "defect_id", flat=True
            )
        defect_ids = [d for d in records if d]
        if not defect_ids:
            return []
        defects = await TestDefect.filter(id__in=defect_ids)
        counts: dict[DefectSeverity, int] = {}
        for d in defects:
            counts[d.severity] = counts.get(d.severity, 0) + 1
        return [DefectSeverityChart(severity=k, count=v) for k, v in counts.items()]

    @classmethod
    async def _list_case_runs_for_suite(cls, suite_run_id: int) -> list[CaseRunDetailOut]:
        records = await ApiCaseRunRecord.filter(suite_run_id=suite_run_id).order_by("id")
        return [
            CaseRunDetailOut(
                id=r.id,
                case_id=r.api_case_id,
                case_name=r.case_name,
                status=r.status,
                duration_ms=r.duration_ms,
                error_message=r.error_message,
                defect_id=r.defect_id,
                start_time=r.start_time,
                end_time=r.end_time,
            )
            for r in records
        ]

    @classmethod
    async def get_suite_report(cls, user: User, suite_run_id: int) -> SuiteReportOut:
        suite_run = await TestSuiteRun.get_or_none(id=suite_run_id)
        if suite_run is None:
            raise AppException("套件运行记录不存在", 404)
        suite = await TestSuite.get_or_none(id=suite_run.suite_id)
        if suite is None:
            raise AppException("套件不存在", 404)
        await ensure_tm_viewer(suite.project_id, user)
        summary = cls._build_summary_from_counters(
            total=suite_run.total_cases,
            passed=suite_run.passed_cases,
            failed=suite_run.failed_cases,
            error=suite_run.error_cases,
            skipped=suite_run.skipped_cases,
            status=suite_run.status,
            start_time=suite_run.start_time,
            end_time=suite_run.end_time,
            duration_ms=suite_run.duration_ms,
        )
        cases = await cls._list_case_runs_for_suite(suite_run_id)
        chart = await cls._defect_chart_for_run(suite_run_id, is_task=False)
        return SuiteReportOut(
            suite_run_id=suite_run_id,
            suite_name=suite.suite_name,
            summary=summary,
            cases=cases,
            defect_chart=chart,
        )

    @classmethod
    async def get_task_report(cls, user: User, task_run_id: int) -> TaskReportOut:
        task_run = await TestTaskRun.get_or_none(id=task_run_id)
        if task_run is None:
            raise AppException("任务运行记录不存在", 404)
        task = await TestTask.get_or_none(id=task_run.task_id)
        if task is None:
            raise AppException("任务不存在", 404)
        await ensure_tm_viewer(task.project_id, user)
        summary = cls._build_summary_from_counters(
            total=task_run.total_cases,
            passed=task_run.passed_cases,
            failed=task_run.failed_cases,
            error=task_run.error_cases,
            skipped=task_run.skipped_cases,
            status=task_run.status,
            start_time=task_run.start_time,
            end_time=task_run.end_time,
            duration_ms=task_run.duration_ms,
        )
        suite_runs = await TestSuiteRun.filter(run_task_id=task_run_id).prefetch_related("suite")
        suites: list[SuiteReportSection] = []
        for sr in suite_runs:
            suite = await TestSuite.get_or_none(id=sr.suite_id)
            s_summary = cls._build_summary_from_counters(
                total=sr.total_cases,
                passed=sr.passed_cases,
                failed=sr.failed_cases,
                error=sr.error_cases,
                skipped=sr.skipped_cases,
                status=sr.status,
                start_time=sr.start_time,
                end_time=sr.end_time,
                duration_ms=sr.duration_ms,
            )
            cases = await cls._list_case_runs_for_suite(sr.id)
            suites.append(
                SuiteReportSection(
                    suite_run_id=sr.id,
                    suite_id=sr.suite_id,
                    suite_name=suite.suite_name if suite else "",
                    summary=s_summary,
                    cases=cases,
                )
            )
        chart = await cls._defect_chart_for_run(task_run_id, is_task=True)
        return TaskReportOut(
            task_run_id=task_run_id,
            task_name=task.task_name,
            summary=summary,
            suites=suites,
            defect_chart=chart,
        )

    @classmethod
    async def get_case_run_log(cls, user: User, case_run_id: int) -> CaseRunLogOut:
        record = await ApiCaseRunRecord.get_or_none(id=case_run_id)
        if record is None:
            raise AppException("用例运行记录不存在", 404)
        project_id = None
        if record.api_case_id:
            from service.api_test.models import ApiTestCase

            case = await ApiTestCase.get_or_none(id=record.api_case_id)
            project_id = case.project_id if case else None
        if project_id is None and record.suite_run_id:
            sr = await TestSuiteRun.get_or_none(id=record.suite_run_id)
            if sr:
                suite = await TestSuite.get_or_none(id=sr.suite_id)
                project_id = suite.project_id if suite else None
        if project_id:
            await ensure_tm_viewer(project_id, user)
        return CaseRunLogOut(
            id=record.id,
            case_name=record.case_name,
            status=record.status,
            case_snapshot=record.case_snapshot,
            api_requests_info=record.api_requests_info,
            log_data=record.log_data,
            error_message=record.error_message,
            duration_ms=record.duration_ms,
        )
