"""知识库管理模块 - document/parse_enrich

parse enrich
"""
from __future__ import annotations

import json
import logging
from typing import Any

from service.core.settings import BASE_DIR, KNOWLEDGE_PARSE_ROOT
from service.core.enums import ActualParseRoute, KnowledgeDocType
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.document.parse_display import to_parsed_interface_item
from service.knowledge.document.parse_paths import resolve_parse_result_path, resolve_storage_file_path
from service.knowledge.document.schemas import ParsedInterfaceItem
from service.knowledge.rules.parse_router import resolve_parse_route
from service.ai_engine.parsers.openapi_document_parser import parse_openapi_file
from service.ai_engine.parsers.swagger_document_parser import parse_swagger_file

logger = logging.getLogger(__name__)


def merge_raw_with_display(raw: dict[str, Any]) -> dict[str, Any]:
    display = to_parsed_interface_item(raw)
    merged = dict(raw)
    merged.update(display)
    return merged


def load_raw_parse_items(version: KnowledgeDocumentVersion) -> list[dict[str, Any]]:
    if not version.parse_result_path:
        return []
    parse_path = resolve_parse_result_path(version.parse_result_path)
    if parse_path is None:
        return []
    try:
        raw_text = parse_path.read_text(encoding="utf-8")
        items = json.loads(raw_text) if raw_text.strip() else []
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]
    except Exception as exc:
        logger.warning("读取 parsed.json 失败 version=%s: %s", version.id, exc)
        return []


def reparse_raw_from_source_file(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
) -> list[dict[str, Any]]:
    if document.doc_type != KnowledgeDocType.api_doc:
        return []
    if version.file_expired or not version.file_path:
        logger.warning(
            "无法从源文件 reparse：原件已过期或路径为空 document=%s version=%s",
            document.id,
            version.id,
        )
        return []

    abs_path = resolve_storage_file_path(version.file_path)
    if abs_path is None or not abs_path.is_file():
        logger.warning(
            "无法从源文件 reparse：文件不存在 document=%s version=%s path=%r",
            document.id,
            version.id,
            version.file_path,
        )
        return []

    content = abs_path.read_bytes()
    route = resolve_parse_route(
        file_name=version.file_name,
        doc_type=document.doc_type,
        parse_mode=document.parse_mode,
        content=content,
    )
    if route == ActualParseRoute.swagger:
        return parse_swagger_file(abs_path)
    if route == ActualParseRoute.openapi:
        return parse_openapi_file(abs_path)
    logger.warning(
        "源文件非 Swagger/OpenAPI 结构化路由 document=%s route=%s file=%s",
        document.id,
        route,
        version.file_name,
    )
    return []


def persist_enriched_parse_result(
    *,
    project_id: int,
    document_id: int,
    version_label: str,
    raw_items: list[dict[str, Any]],
) -> str:
    enriched = [merge_raw_with_display(item) for item in raw_items if isinstance(item, dict)]
    dest_dir = KNOWLEDGE_PARSE_ROOT / str(project_id) / str(document_id) / version_label
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "parsed.json"
    dest.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(dest.relative_to(BASE_DIR))
