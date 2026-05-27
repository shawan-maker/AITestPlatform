import pytest

from service.core.enums import DefectStatus
from service.core.exceptions import AppException
from service.test_management.defect.transition import validate_transition


class TestDefectTransition:
    def test_init_to_open(self):
        validate_transition(DefectStatus.init, DefectStatus.open)

    def test_closed_to_open_reopen(self):
        validate_transition(DefectStatus.closed, DefectStatus.open)

    def test_init_to_closed_rejected(self):
        with pytest.raises(AppException) as exc:
            validate_transition(DefectStatus.init, DefectStatus.closed)
        assert exc.value.code == 400

    def test_same_status_rejected(self):
        with pytest.raises(AppException) as exc:
            validate_transition(DefectStatus.open, DefectStatus.open)
        assert exc.value.code == 400

    def test_in_progress_to_resolved(self):
        validate_transition(DefectStatus.in_progress, DefectStatus.resolved)

    def test_resolved_to_in_progress(self):
        validate_transition(DefectStatus.resolved, DefectStatus.in_progress)
