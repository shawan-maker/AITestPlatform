from pathlib import Path

from service.core.enums import ActualParseRoute, KnowledgeDocType, ParseMode
from service.knowledge.rules.file_rules import API_SPEC_EXTENSIONS, detect_api_spec_kind

MULTIMODAL_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".webp"}


def resolve_parse_route(
    *,
    file_name: str,
    doc_type: KnowledgeDocType,
    parse_mode: ParseMode,
    content: bytes,
) -> ActualParseRoute:
    ext = Path(file_name).suffix.lower()
    # 显式选择的解析方式优先，不走自动检测
    if parse_mode == ParseMode.swagger:
        return ActualParseRoute.swagger
    if parse_mode == ParseMode.openapi:
        return ActualParseRoute.openapi

    # AI 智能解析模式：始终走 AI 路由，不因文件扩展名降级为 swagger/openapi
    # 这样确保重新上传时使用与首次上传一致的解析方式
    if parse_mode == ParseMode.ai:
        if ext in MULTIMODAL_EXTENSIONS:
            return ActualParseRoute.ai_multimodal
        return ActualParseRoute.ai_text

    # 自动检测模式（auto）
    if ext in API_SPEC_EXTENSIONS:
        kind = detect_api_spec_kind(content)
        if kind == "swagger":
            return ActualParseRoute.swagger
        if kind == "openapi":
            return ActualParseRoute.openapi
        if kind is None:
            return ActualParseRoute.auto_text

    if ext in MULTIMODAL_EXTENSIONS:
        return ActualParseRoute.ai_multimodal
    return ActualParseRoute.auto_text
