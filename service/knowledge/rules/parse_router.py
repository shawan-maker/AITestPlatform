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
    if parse_mode == ParseMode.swagger:
        return ActualParseRoute.swagger
    if parse_mode == ParseMode.openapi:
        return ActualParseRoute.openapi

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
    return ActualParseRoute.ai_text
