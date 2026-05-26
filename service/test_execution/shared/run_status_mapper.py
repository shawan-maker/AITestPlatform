from service.core.enums import CaseRunStatus, RunStatus


def map_case_run_status_to_label(status: CaseRunStatus) -> str:
    mapping = {
        CaseRunStatus.success: "成功",
        CaseRunStatus.fail: "失败",
        CaseRunStatus.error: "异常",
    }
    return mapping.get(status, status.value)


def map_run_status_to_label(status: RunStatus) -> str:
    mapping = {
        RunStatus.pending: "待执行",
        RunStatus.running: "执行中",
        RunStatus.completed: "已完成",
        RunStatus.failed: "失败",
        RunStatus.cancelled: "已停止",
    }
    return mapping.get(status, status.value)


def is_terminal_run_status(status: RunStatus) -> bool:
    return status in (
        RunStatus.completed,
        RunStatus.failed,
        RunStatus.cancelled,
    )
