"""测试管理模块 - defect/transition

transition
"""
from service.core.enums import DefectStatus
from service.core.exceptions import AppException

ALLOWED_TRANSITIONS: dict[DefectStatus, set[DefectStatus]] = {
    DefectStatus.init: {DefectStatus.open},
    DefectStatus.open: {DefectStatus.in_progress, DefectStatus.closed},
    DefectStatus.in_progress: {DefectStatus.open, DefectStatus.resolved},
    DefectStatus.resolved: {DefectStatus.closed, DefectStatus.in_progress},
    DefectStatus.closed: {DefectStatus.open},
}


def validate_transition(current: DefectStatus, target: DefectStatus) -> None:
    if current == target:
        raise AppException("目标状态与当前状态相同", 400)
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise AppException(
            f"不允许从 {current.value} 流转到 {target.value}",
            400,
        )
