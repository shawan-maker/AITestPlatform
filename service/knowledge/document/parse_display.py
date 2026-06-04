from __future__ import annotations

from typing import Any


def _param_names(plist: list) -> list[str]:
    names: list[str] = []
    for p in plist:
        if isinstance(p, dict) and p.get("name"):
            names.append(str(p.get("name")))
        elif hasattr(p, "name") and p.name:
            names.append(str(p.name))
    return names


def format_request_modules(item: dict[str, Any]) -> str:
    parts: list[str] = []
    params = item.get("parameters")
    if isinstance(params, dict):
        for loc in ("header", "path", "query"):
            plist = params.get(loc) or []
            if not isinstance(plist, list):
                continue
            names = _param_names(plist)
            if names:
                parts.append(f"{loc}: {', '.join(names)}")
    elif isinstance(params, list):
        by_loc: dict[str, list[str]] = {}
        body_names: list[str] = []
        for p in params:
            if not isinstance(p, dict):
                continue
            loc = p.get("in") or p.get("location")
            name = p.get("name")
            if loc in ("header", "path", "query") and name:
                by_loc.setdefault(loc, []).append(str(name))
            elif loc in ("body", "formData") and name:
                body_names.append(str(name))
        for loc in ("header", "path", "query"):
            if by_loc.get(loc):
                parts.append(f"{loc}: {', '.join(by_loc[loc])}")
        if body_names:
            parts.append(f"body: {', '.join(body_names)}")

    request_body = item.get("requestBody") or item.get("request_body")
    if isinstance(request_body, dict):
        body_fields = request_body.get("body") or []
        if isinstance(body_fields, list):
            body_names = _param_names(body_fields)
            if body_names:
                parts.append(f"body: {', '.join(body_names)}")
        props = request_body.get("properties")
        if isinstance(props, dict) and props:
            prop_names = [str(k) for k in props.keys()]
            if prop_names:
                parts.append(f"body: {', '.join(prop_names)}")
        content = request_body.get("content")
        if isinstance(content, dict):
            for _, media in content.items():
                if not isinstance(media, dict):
                    continue
                schema = media.get("schema") or {}
                if isinstance(schema, dict):
                    schema_props = schema.get("properties")
                    if isinstance(schema_props, dict) and schema_props:
                        prop_names = [str(k) for k in schema_props.keys()]
                        if prop_names:
                            parts.append(f"body: {', '.join(prop_names)}")

    return "; ".join(parts)


def format_api_doc_path(item: dict[str, Any]) -> str:
    tags = item.get("tags") or []
    if isinstance(tags, list) and tags:
        return " / ".join(str(t) for t in tags if t)

    path = (item.get("path") or "").strip()
    if not path or path == "/":
        return ""

    segments = [s for s in path.strip("/").split("/") if s and not s.startswith("{")]
    if not segments:
        return path
    if len(segments) == 1:
        return segments[0]
    return " / ".join(segments[:-1])


def to_parsed_interface_item(item: dict[str, Any]) -> dict[str, Any]:
    method = (item.get("method") or "").upper()
    path = item.get("path") or ""
    summary = item.get("summary")
    if summary is not None:
        summary = str(summary)
    return {
        "method": method,
        "path": path,
        "summary": summary or None,
        "request_modules": format_request_modules(item) or None,
        "api_path": format_api_doc_path(item) or None,
    }
