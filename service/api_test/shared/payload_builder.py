from typing import Any


def build_debug_payload_from_interface(iface) -> dict[str, Any]:
    params = iface.parameters or {}
    headers = {p.get("name", ""): p.get("example") for p in params.get("header", []) if p.get("name")}
    query = {p.get("name", ""): p.get("example") for p in params.get("query", []) if p.get("name")}
    path_params = {p.get("name", ""): p.get("example") for p in params.get("path", []) if p.get("name")}
    body = None
    if iface.request_body:
        content = iface.request_body.get("content") or {}
        for media in content.values():
            if isinstance(media, dict) and "example" in media:
                body = media["example"]
                break
    return {
        "method": iface.method,
        "path": iface.path,
        "headers": headers,
        "query": query,
        "path_params": path_params,
        "body": body,
    }


def build_runner_case_from_payload(
    iface,
    payload: dict[str, Any] | None,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    base = payload or build_debug_payload_from_interface(iface)
    return {
        "title": title or iface.summary or f"{iface.method} {iface.path}",
        "method": base.get("method") or iface.method,
        "path": base.get("path") or iface.path,
        "headers": base.get("headers") or {},
        "query": base.get("query") or {},
        "path_params": base.get("path_params") or {},
        "body": base.get("body"),
        "assertions": base.get("assertions") or [],
        "preconditions": base.get("preconditions") or [],
    }
