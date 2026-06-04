"""解析接口列表单一管道：展示字段 + 已保存模块/目录。"""

from __future__ import annotations

import logging
from typing import Any

from service.core.enums import KnowledgeDocType, ParseStatus
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.document.parse_display import to_parsed_interface_item
from service.knowledge.document.parse_enrich import (
    load_raw_parse_items,
    persist_enriched_parse_result,
    reparse_raw_from_source_file,
)
from service.knowledge.document.saved_interface_loader import merge_saved_interface_info
from service.knowledge.document.schemas import ParsedInterfaceItem

logger = logging.getLogger(__name__)


def _interface_key(method: str, path: str) -> str:
    return f"{(method or '').upper()}:{path or ''}"


def item_needs_display_fields(item: ParsedInterfaceItem) -> bool:
    return not (item.request_modules or item.api_path)


def build_parsed_item_from_raw(raw: dict[str, Any]) -> ParsedInterfaceItem | None:
    if not raw.get("method") or not raw.get("path"):
        return None
    display = to_parsed_interface_item(raw)
    if not display.get("request_modules") and raw.get("request_modules"):
        display["request_modules"] = raw.get("request_modules")
    if not display.get("api_path") and raw.get("api_path"):
        display["api_path"] = raw.get("api_path")
    return ParsedInterfaceItem(**display)


def items_from_raw_list(raw_items: list[dict[str, Any]]) -> list[ParsedInterfaceItem]:
    result: list[ParsedInterfaceItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item = build_parsed_item_from_raw(raw)
        if item is not None:
            result.append(item)
    return result


async def _persist_and_update_version_path(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
    raw_items: list[dict[str, Any]],
) -> None:
    if not raw_items:
        return
    try:
        relative_path = persist_enriched_parse_result(
            project_id=document.project_id,
            document_id=document.id,
            version_label=version.version_label,
            raw_items=raw_items,
        )
        if version.parse_result_path != relative_path:
            version.parse_result_path = relative_path
            await version.save(update_fields=["parse_result_path"])
    except OSError as exc:
        logger.warning(
            "写入 enriched parsed.json 失败 document=%s version=%s: %s",
            document.id,
            version.id,
            exc,
        )


def _load_items_from_cached_json(
    version: KnowledgeDocumentVersion,
) -> list[ParsedInterfaceItem]:
    return items_from_raw_list(load_raw_parse_items(version))


def _merge_display_from_cache(
    primary: list[ParsedInterfaceItem],
    cached: list[ParsedInterfaceItem],
) -> list[ParsedInterfaceItem]:
    by_key = {_interface_key(i.method, i.path): i for i in cached}
    merged: list[ParsedInterfaceItem] = []
    for item in primary:
        if item_needs_display_fields(item):
            better = by_key.get(_interface_key(item.method, item.path))
            merged.append(better if better and not item_needs_display_fields(better) else item)
        else:
            merged.append(item)
    return merged


async def resolve_parsed_interfaces(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
) -> list[ParsedInterfaceItem]:
    if document.doc_type != KnowledgeDocType.api_doc:
        return []
    if _enum_value(version.parse_status) != ParseStatus.parsed.value:
        return []

    raw_from_file = reparse_raw_from_source_file(document, version)
    if raw_from_file:
        items = items_from_raw_list(raw_from_file)
        await _persist_and_update_version_path(document, version, raw_from_file)
    else:
        items = _load_items_from_cached_json(version)

    if items and any(item_needs_display_fields(item) for item in items):
        cached = _load_items_from_cached_json(version)
        if cached:
            items = _merge_display_from_cache(items, cached)

    if not items and raw_from_file:
        items = items_from_raw_list(raw_from_file)

    return await merge_saved_interface_info(document, version, items)


def _enum_value(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)
