from service.test_management.shared.last_run_query import format_success_rate


class TestLastRunQuery:
    def test_format_success_rate_none_when_zero(self):
        assert format_success_rate(0, 0) is None

    def test_format_success_rate_display(self):
        assert format_success_rate(1, 2) == "50.0% (1/2)"
