from service.core.enums import DefectCategory, DefectStatus


class TestDefectCategory:
    def test_all_category_values(self):
        assert {c.value for c in DefectCategory} == {
            "functional",
            "performance",
            "ui",
            "compatibility",
            "security",
            "other",
        }

    def test_default_category_is_other(self):
        assert DefectCategory.other.value == "other"


class TestDefectStatus:
    def test_extended_status_values(self):
        assert {s.value for s in DefectStatus} == {
            "init",
            "open",
            "in_progress",
            "resolved",
            "closed",
        }

    def test_in_progress_and_resolved_members(self):
        assert DefectStatus.in_progress.value == "in_progress"
        assert DefectStatus.resolved.value == "resolved"
