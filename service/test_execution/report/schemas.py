"""测试执行模块 - report/schemas

请求/响应 Schema 定义
"""
from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import CaseRunStatus, DefectSeverity, RunStatus


class ReportSummaryOut(BaseModel):
    """报告summaryout"""
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
    """缺陷严重程度chart"""
    severity: DefectSeverity
    count: int


class CaseRunDetailOut(BaseModel):
    """用例执行detailout"""
    id: int
    case_id: int | None
    case_name: str
    status: str  # CaseRunStatus or "pending" for not-started cases
    duration_ms: int | None = None
    error_message: str | None = None
    defect_id: int | None = None
    defect_title: str | None = None
    defect_code: str | None = None
    external_key: str | None = None
    interface_method: str | None = None
    interface_path: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class SuiteReportSection(BaseModel):
    """套件报告section"""
    suite_run_id: int
    suite_id: int
    suite_name: str
    summary: ReportSummaryOut
    cases: list[CaseRunDetailOut] = []


class SuiteReportOut(BaseModel):
    """套件报告out"""
    suite_run_id: int
    suite_name: str
    task_name: str | None = None
    triggered_by_name: str | None = None
    summary: ReportSummaryOut
    cases: list[CaseRunDetailOut]
    defect_chart: list[DefectSeverityChart] = []


class TaskReportOut(BaseModel):
    """任务报告out"""
    task_run_id: int
    task_name: str
    summary: ReportSummaryOut
    suites: list[SuiteReportSection]
    defect_chart: list[DefectSeverityChart] = []


class CaseRunLogOut(BaseModel):
    """用例执行logout"""
    id: int
    case_name: str
    status: CaseRunStatus
    case_snapshot: dict | None = None
    api_requests_info: dict | None = None
    log_data: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
