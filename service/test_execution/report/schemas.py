from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import CaseRunStatus, DefectSeverity, RunStatus


class ReportSummaryOut(BaseModel):
    total: int
    passed: int
    failed: int
    error: int
    skipped: int
    pass_rate: float
    pass_rate_display: str
    status: RunStatus
    start_time: datetime | None
    end_time: datetime | None
    duration_ms: int | None


class DefectSeverityChart(BaseModel):
    severity: DefectSeverity
    count: int


class CaseRunDetailOut(BaseModel):
    id: int
    case_id: int | None
    case_name: str
    status: CaseRunStatus
    duration_ms: int | None
    error_message: str | None = None
    defect_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class SuiteReportSection(BaseModel):
    suite_run_id: int
    suite_id: int
    suite_name: str
    summary: ReportSummaryOut
    cases: list[CaseRunDetailOut] = []


class SuiteReportOut(BaseModel):
    suite_run_id: int
    suite_name: str
    summary: ReportSummaryOut
    cases: list[CaseRunDetailOut]
    defect_chart: list[DefectSeverityChart] = []


class TaskReportOut(BaseModel):
    task_run_id: int
    task_name: str
    summary: ReportSummaryOut
    suites: list[SuiteReportSection]
    defect_chart: list[DefectSeverityChart] = []


class CaseRunLogOut(BaseModel):
    id: int
    case_name: str
    status: CaseRunStatus
    case_snapshot: dict | None = None
    api_requests_info: dict | None = None
    log_data: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
