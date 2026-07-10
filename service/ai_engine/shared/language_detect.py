"""语言检测与 locale 转换工具。

用于 AI 智能体根据输入内容或前端 locale 判定输出语言。
"""


def detect_language(text: str) -> str:
    """检测文本的主要语言，返回 'zh' 或 'en'。

    基于 CJK 统一汉字在字母字符中的占比：
    - CJK 占比 > 15% → 'zh'
    - 否则 → 'en'
    - 空文本或无字母字符 → 'zh'（默认中文）

    适用场景：需求文档、user_prompt 等自然语言文本。
    不适用于 API 文档（代码/符号密集，CJK 占比会被稀释）。
    """
    if not text:
        return "zh"

    cjk_count = 0
    alpha_count = 0
    for ch in text[:3000]:
        if ch.isalpha():
            alpha_count += 1
            if '一' <= ch <= '鿿':
                cjk_count += 1

    if alpha_count == 0:
        return "zh"

    return "zh" if cjk_count / alpha_count > 0.15 else "en"


def locale_to_language(locale: str | None) -> str:
    """前端 i18n locale 转 output_language。

    zh-CN / zh-TW / zh → 'zh'
    en-US / en / 其他   → 'en'
    None               → 'zh'（默认）
    """
    if not locale:
        return "zh"
    return "zh" if locale.startswith("zh") else "en"
