from __future__ import annotations

from service.api_test.interface.models import ApiInterface, ApiInterfaceCatalog
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.document.parse_display import to_parsed_interface_item
from service.knowledge.document.parse_enrich import load_raw_parse_items
from service.knowledge.document.schemas import ParsedInterfaceItem
from service.project.models import ProjectModule


async def _catalog_path_map(project_id: int, catalog_ids: set[int]) -> dict[int, str]:
    if not catalog_ids:
        return {}
    rows = await ApiInterfaceCatalog.filter(project_id=project_id).values(
        "id", "parent_id", "name"
    )
    by_id = {row["id"]: row for row in rows}

    def build_path(catalog_id: int) -> str:
        parts: list[str] = []
        current: int | None = catalog_id
        seen: set[int] = set()
        while current is not None and current not in seen:
            seen.add(current)
            row = by_id.get(current)
            if row is None:
                break
            parts.append(str(row["name"]))
            current = row["parent_id"]
        return " / ".join(reversed(parts))

    return {cid: build_path(cid) for cid in catalog_ids if cid in by_id}


def _iface_display_raw(
    saved: dict,
    item: ParsedInterfaceItem | None = None,
    *,
    raw_source: dict | None = None,
) -> dict:
    method = (saved.get("method") or (item.method if item else "") or "").upper()
    path = saved.get("path") or (item.path if item else "") or ""
    source = raw_source or {}
    return {
        "method": method,
        "path": path,
        "summary": (item.summary if item else None) or saved.get("summary") or source.get("summary"),
        "parameters": saved.get("parameters") or source.get("parameters") or {},
        "requestBody": saved.get("request_body") or source.get("requestBody") or source.get("request_body"),
        "tags": source.get("tags") or saved.get("tags") or [],
    }


def _raw_lookup(version: KnowledgeDocumentVersion) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for raw in load_raw_parse_items(version):
        method = (raw.get("method") or "").upper()
        path = raw.get("path") or ""
        if method and path:
            lookup[f"{method}:{path}"] = raw
    return lookup


def _enrich_from_saved(
    item: ParsedInterfaceItem,
    saved: dict,
    *,
    module_name: str | None,
    catalog_path: str | None,
    raw_source: dict | None = None,
) -> ParsedInterfaceItem:
    raw = _iface_display_raw(saved, item, raw_source=raw_source)
    updates: dict = {
        "module_name": module_name,
        "catalog_path": catalog_path or None,
    }
    if not item.summary and raw.get("summary"):
        updates["summary"] = str(raw["summary"])
    return item.model_copy(update=updates)


async def merge_saved_interface_info(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
    items: list[ParsedInterfaceItem],
) -> list[ParsedInterfaceItem]:
    raw_by_key = _raw_lookup(version)

    saved_rows = list(
        await ApiInterface.filter(
            source_document_id=document.id,
            is_current=True,
        ).values(
            "method",
            "path",
            "summary",
            "module_id",
            "catalog_id",
            "parameters",
            "request_body",
        )
    )

    if not saved_rows:
        enriched: list[ParsedInterfaceItem] = []
        for item in items:
            key = f"{item.method.upper()}:{item.path}"
            raw = raw_by_key.get(key)
            if raw:
                enriched.append(ParsedInterfaceItem(**to_parsed_interface_item(raw)))
            else:
                enriched.append(item)
        return enriched

    module_ids = {row["module_id"] for row in saved_rows if row["module_id"]}
    catalog_ids = {row["catalog_id"] for row in saved_rows if row["catalog_id"]}

    module_names: dict[int, str] = {}
    if module_ids:
        modules = await ProjectModule.filter(id__in=list(module_ids)).values("id", "name")
        module_names = {row["id"]: row["name"] for row in modules}

    catalog_paths = await _catalog_path_map(document.project_id, catalog_ids)

    saved_by_key = {
        f"{(row['method'] or '').upper()}:{row['path']}": row for row in saved_rows
    }

    if not items:
        built: list[ParsedInterfaceItem] = []
        for saved in saved_rows:
            method = (saved.get("method") or "").upper()
            path = saved.get("path") or ""
            if not method or not path:
                continue
            raw_source = raw_by_key.get(f"{method}:{path}")
            raw = _iface_display_raw(saved, raw_source=raw_source)
            display = to_parsed_interface_item(raw)
            module_name = (
                module_names.get(saved["module_id"]) if saved.get("module_id") else None
            )
            catalog_path = (
                catalog_paths.get(saved["catalog_id"]) if saved.get("catalog_id") else None
            )
            built.append(
                ParsedInterfaceItem(
                    **display,
                    module_name=module_name,
                    catalog_path=catalog_path or None,
                )
            )
        return built

    result: list[ParsedInterfaceItem] = []
    for item in items:
        key = f"{item.method.upper()}:{item.path}"
        saved = saved_by_key.get(key)
        if saved is None:
            raw = raw_by_key.get(key)
            if raw:
                result.append(ParsedInterfaceItem(**to_parsed_interface_item(raw)))
            else:
                result.append(item)
            continue
        module_name = (
            module_names.get(saved["module_id"]) if saved.get("module_id") else None
        )
        catalog_path = (
            catalog_paths.get(saved["catalog_id"]) if saved.get("catalog_id") else None
        )
        result.append(
            _enrich_from_saved(
                item,
                saved,
                module_name=module_name,
                catalog_path=catalog_path,
                raw_source=raw_by_key.get(key),
            )
        )
    return result


async def load_parsed_interfaces_with_saved_info(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
) -> list[ParsedInterfaceItem]:
    from service.knowledge.document.parsed_interface_service import resolve_parsed_interfaces

    return await resolve_parsed_interfaces(document, version)
