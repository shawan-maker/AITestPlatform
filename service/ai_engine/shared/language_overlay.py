"""LLM 输出语言覆盖指令。

在现有中文 prompt 末尾追加 language_overlay 变量，
指示 LLM 使用指定语言输出。中文时为空串（默认行为不变）。
"""

_LANGUAGE_OVERLAY_EN = """\

## OUTPUT LANGUAGE REQUIREMENT

All output MUST be in **English**, including:
- Test case names, descriptions, steps, preconditions, expected results
- Test point types and dimensions
- Assertion type keywords (e.g., use "equals" instead of "相等")
- Dependency names in the `dependencies` array
- Any transitional or status text

### Interface Name Translation
- When a bilingual name table is provided above, ALWAYS use the **English Name** column for `dependencies`
- Test case `name` field must also use English interface names (e.g., "GET Get Image Captcha - Normal Request" not "GET 获取图片验证码 - 正常请求")
- Example: if the table shows "登录" → "Login", use "Login" in dependencies, NOT "登录"

### CRITICAL EXCEPTION — Do NOT translate assertion expected values:
- In `assertions[].expected` fields and `expected` arrays, the **actual comparison values** MUST be preserved exactly as they appear in the API document's example responses.
- For example, if the API response example contains `{"description": "注册成功"}`, the assertion expected value MUST be `"注册成功"`, NOT `"Registration successful"`.
- Only the assertion **type** field should be translated (e.g., "相等" → "equals", "包含" → "contains").
- The assertion **expected** value must match what the API actually returns — translating it would cause assertion failures at runtime.

Use the following field value mappings:
- "功能测试" → "Functional Test"
- "正向验证" → "Positive Validation"
- "边界测试" → "Boundary Test"
- "异常测试" → "Exception Test"
- "性能测试" → "Performance Test"
- "安全测试" → "Security Test"
- "兼容性测试" → "Compatibility Test"
- "易用性测试" → "Usability Test"
- "相等" → "equals"
- "包含" → "contains"
- "大于" → "greater_than"
- "小于" → "less_than"
- "不为空" → "not_empty"
- "为空" → "is_empty"
- "包含(忽略大小写)" → "contains_ignore_case"
"""

# TRANSITIONAL 标记双语版本
TRANSITIONAL_MESSAGES = {
    "zh": "[TRANSITIONAL] 📋 需求检索完成，正在梳理需求要点，准备生成测试点与测试用例...",
    "en": "[TRANSITIONAL] 📋 Requirement retrieval complete, organizing key points, preparing to generate test cases...",
}

# 覆盖率判定标记双语版本
COVERAGE_COMPLETE_MARKERS = [
    "测试点已经全部覆盖",
    "All test points are fully covered",
    "已经覆盖全部测试点",
    "All test points are already covered",
]


def get_language_overlay(lang: str) -> str:
    """根据语言返回 overlay 指令。中文返回空串，英文返回英文指令。"""
    if lang == "en":
        return _LANGUAGE_OVERLAY_EN
    return ""


def get_transitional_message(lang: str) -> str:
    """获取 TRANSITIONAL 标记文本。"""
    return TRANSITIONAL_MESSAGES.get(lang, TRANSITIONAL_MESSAGES["zh"])


def is_coverage_complete(result: str) -> bool:
    """判断覆盖率验证结果是否表示"已全部覆盖"。同时检查中英文标记。"""
    return any(marker in result for marker in COVERAGE_COMPLETE_MARKERS)
