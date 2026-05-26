import pytest

from service.core.exceptions import AppException
from service.test_execution.defect.schemas import DefectBatchLinkRequest
from service.test_execution.shared.run_status_mapper import (
    is_terminal_run_status,
    map_run_status_to_label,
)
from service.test_execution.shared.summary_calculator import (
    compute_run_status,
    format_pass_rate,
    pass_rate,
)
from service.core.enums import RunStatus


class TestSummaryCalculator:
    def test_pass_rate_zero_total(self):
        assert pass_rate(0, 0) == 0.0
        assert format_pass_rate(0, 0) == "0.0% (0/0)"

    def test_pass_rate_normal(self):
        assert pass_rate(2, 4) == 0.5
        assert format_pass_rate(2, 4) == "50.0% (2/4)"

    def test_compute_run_status_cancelled(self):
        assert (
            compute_run_status(
                passed=1, failed=0, error=0, skipped=0, total=2, cancelled=True
            )
            == RunStatus.cancelled
        )

    def test_compute_run_status_any_fail_is_fail(self):
        assert (
            compute_run_status(
                passed=3, failed=1, error=0, skipped=0, total=4, cancelled=False
            )
            == RunStatus.failed
        )
        assert (
            compute_run_status(
                passed=3, failed=0, error=1, skipped=0, total=4, cancelled=False
            )
            == RunStatus.failed
        )

    def test_compute_run_status_completed(self):
        assert (
            compute_run_status(
                passed=4, failed=0, error=0, skipped=0, total=4, cancelled=False
            )
            == RunStatus.completed
        )


class TestRunStatusMapper:
    def test_terminal_statuses(self):
        assert is_terminal_run_status(RunStatus.completed)
        assert is_terminal_run_status(RunStatus.failed)
        assert is_terminal_run_status(RunStatus.cancelled)
        assert not is_terminal_run_status(RunStatus.running)

    def test_label_mapping(self):
        assert map_run_status_to_label(RunStatus.cancelled) == "已停止"


class TestDefectBatchLinkRules:
    def test_accepts_external_key_only(self):
        req = DefectBatchLinkRequest(case_run_ids=[1], external_key="BUG-1")
        assert req.external_key == "BUG-1"
        assert req.defect_id is None

    def test_accepts_defect_id_only(self):
        req = DefectBatchLinkRequest(case_run_ids=[1], defect_id=99)
        assert req.defect_id == 99


class TestDefectServiceValidation:
    @pytest.mark.asyncio
    async def test_batch_link_requires_key_or_id(self):
        from service.test_execution.defect.defect_service import DefectService
        from service.test_execution.defect.schemas import DefectBatchLinkRequest

        with pytest.raises(AppException) as exc:
            await DefectService.batch_link(
                None, DefectBatchLinkRequest(case_run_ids=[1])
            )
        assert exc.value.code == 400

    @pytest.mark.asyncio
    async def test_batch_link_rejects_both_keys(self):
        from service.test_execution.defect.defect_service import DefectService
        from service.test_execution.defect.schemas import DefectBatchLinkRequest

        with pytest.raises(AppException) as exc:
            await DefectService.batch_link(
                None,
                DefectBatchLinkRequest(
                    case_run_ids=[1], external_key="x", defect_id=1
                ),
            )
        assert exc.value.code == 400
