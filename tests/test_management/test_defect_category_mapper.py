from service.core.enums import DefectCategory, FunctionalCaseType
from service.test_management.defect.category_mapper import (
    infer_category_from_api_case,
    infer_category_from_functional,
    infer_from_test_point_type,
)


class TestCategoryMapper:
    def test_test_point_type_functional(self):
        assert infer_from_test_point_type("功能测试") == DefectCategory.functional

    def test_test_point_type_performance(self):
        assert infer_from_test_point_type("性能测试") == DefectCategory.performance

    def test_test_point_type_security(self):
        assert infer_from_test_point_type("安全测试") == DefectCategory.security

    def test_functional_case_ui_fallback(self):
        assert (
            infer_category_from_functional(case_type=FunctionalCaseType.ui)
            == DefectCategory.ui
        )

    def test_functional_case_priority_chain(self):
        assert (
            infer_category_from_functional(
                test_point_type="兼容性测试",
                dimension="浏览器兼容",
                case_type=FunctionalCaseType.functional,
            )
            == DefectCategory.compatibility
        )

    def test_api_case_defaults_other(self):
        assert infer_category_from_api_case() == DefectCategory.other
