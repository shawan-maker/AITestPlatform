from service.core.enums import CaseCategory, DefectCategory


def infer_from_test_point_type(type_text: str | None) -> DefectCategory | None:
    if not type_text:
        return None
    text = type_text.strip()
    lowered = text.lower()
    if "功能" in text or "functional" in lowered:
        return DefectCategory.functional
    if "性能" in text or "performance" in lowered:
        return DefectCategory.performance
    if "界面" in text or "易用" in text or "ui" in lowered or "usability" in lowered:
        return DefectCategory.ui
    if "兼容" in text or "compatibility" in lowered:
        return DefectCategory.compatibility
    if "安全" in text or "security" in lowered:
        return DefectCategory.security
    return None


def infer_from_dimension(dimension: str | None) -> DefectCategory | None:
    if not dimension:
        return None
    return infer_from_test_point_type(dimension)


def infer_from_case_category(case_category: CaseCategory) -> DefectCategory:
    """从用例分类推断缺陷分类（SIT-09）"""
    mapping = {
        CaseCategory.functional: DefectCategory.functional,
        CaseCategory.performance: DefectCategory.performance,
        CaseCategory.security: DefectCategory.security,
        CaseCategory.compatibility: DefectCategory.compatibility,
        CaseCategory.usability: DefectCategory.ui,  # usability -> ui
        CaseCategory.other: DefectCategory.other,
    }
    return mapping.get(case_category, DefectCategory.other)


def infer_category_from_functional(
    *,
    test_point_type: str | None = None,
    dimension: str | None = None,
    case_category: CaseCategory | None = None,
) -> DefectCategory:
    for candidate in (
        infer_from_test_point_type(test_point_type),
        infer_from_dimension(dimension),
        infer_from_case_category(case_category) if case_category else None,
    ):
        if candidate is not None:
            return candidate
    return DefectCategory.other


def infer_category_from_api_case() -> DefectCategory:
    return DefectCategory.other
