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


def _extract_script(items: list | None) -> str:
    """Extract Python code from [{kind:'python', code:'...'}] list into a plain string.

    Automatically prepends 'from ApiEngine import global_func' so that
    user scripts can call global_func.method_name() without manual import.
    """
    if not items:
        return ""
    parts = []
    for item in items:
        if isinstance(item, dict):
            code = item.get("code")
            if isinstance(code, str) and code.strip():
                parts.append(code)
        elif isinstance(item, str):
            parts.append(item)
    combined = "\n".join(parts)
    # Only inject if there is real code (not just comments/whitespace)
    import re
    if re.sub(r'#[^\n]*', '', combined).strip():
        combined = "from ApiEngine import global_func\n" + combined
    return combined


def _convert_precondition(step: dict) -> dict:
    """Convert a single API-call precondition into ApiEngine step format.

    Note: Python-only preconditions (kind='python') should NOT go through
    this function — they are extracted as setup_script/teardown_script
    in build_runner_case_from_payload to avoid phantom HTTP requests.
    """
    path = step.get("path", "")
    method = step.get("method", "GET")
    headers = step.get("headers") or {}
    query = step.get("query") or step.get("params") or {}
    body = step.get("body") or {}
    content_type = headers.get("Content-Type", "")

    request_block: dict[str, Any] = {"params": query}
    if "application/json" in content_type:
        request_block["json"] = body
    else:
        request_block["data"] = body

    result: dict[str, Any] = {
        "title": step.get("title") or f"{method} {path}",
        "interface": {"url": path, "method": method.lower()},
        "headers": headers,
        "request": request_block,
        "setup_script": _extract_script(step.get("setup_scripts")),
        "teardown_script": _extract_script(step.get("teardown_scripts")),
    }

    # Nested preconditions (recursive, API-call only)
    sub = step.get("preconditions")
    if sub and isinstance(sub, list):
        nested = [_convert_precondition(s) for s in sub if isinstance(s, dict) and s.get("kind") != "python"]
        if nested:
            result["preconditions"] = nested

    # Extracts
    extracts = step.get("extracts") or step.get("extract")
    if extracts:
        result["extract"] = _convert_extracts(extracts)

    # Assertions
    assertions = step.get("assertions")
    if assertions:
        result["assertions"] = _convert_assertions(assertions)

    return result


def _convert_extracts(extracts: list) -> list:
    """Convert frontend extract format to ApiEngine format.

    Frontend: [{"name": "...", "expression": "...", ...}]
    Engine:   [{"var_name": "...", "extract_expr": "..."}]
    """
    result = []
    for item in extracts:
        if not isinstance(item, dict):
            continue
        var_name = item.get("var_name") or item.get("name")
        extract_expr = (
            item.get("extract_expr")
            or item.get("expression")
            or item.get("json_path")
            or item.get("expr")
        )
        if var_name and extract_expr:
            result.append({"var_name": var_name, "extract_expr": extract_expr})
    return result


def _convert_assertions(assertions: list) -> list:
    """Convert frontend assertion format to ApiEngine format.

    Frontend: [{"target": "...", "comparator": "...", "expected": ...}]
    Engine:   [{"type": "...", "field": "...", "expected": ...}]
    """
    result = []
    for item in assertions:
        if not isinstance(item, dict):
            continue
        assertion_type = (
            item.get("type")
            or item.get("comparator")
            or item.get("compare")
            or "eq"
        )
        field = item.get("field") or item.get("target") or item.get("source")
        expected = item.get("expected") if "expected" in item else item.get("expect")
        if field is not None:
            result.append({"type": assertion_type, "field": field, "expected": expected})
    return result


def _apply_path_params(path: str, path_params: dict) -> str:
    """Replace {param} placeholders in path with actual values."""
    if not path_params:
        return path
    for key, value in path_params.items():
        path = path.replace(f"{{{key}}}", str(value))
    return path


def build_runner_case_from_payload(
    iface,
    payload: dict[str, Any] | None,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    base = payload or build_debug_payload_from_interface(iface)

    method = base.get("method") or iface.method
    raw_path = base.get("path") or iface.path
    path_params = base.get("path_params") or {}
    path = _apply_path_params(raw_path, path_params)
    headers = base.get("headers") or {}
    query = base.get("query") or {}
    body = base.get("body")
    content_type = headers.get("Content-Type", "")

    # Build nested request block
    request_block: dict[str, Any] = {"params": query}
    if body is not None:
        if "application/json" in content_type:
            request_block["json"] = body
        else:
            request_block["data"] = body
    else:
        request_block["data"] = {}
        request_block["json"] = {}

    # --- Setup/Teardown scripts ---
    # Python preconditions → main case setup_script (avoid phantom HTTP requests)
    # Python postconditions → main case teardown_script
    raw_preconditions = base.get("preconditions") or []
    raw_postconditions = base.get("postconditions") or []

    pre_python_code = _extract_script([
        s for s in raw_preconditions
        if isinstance(s, dict) and s.get("kind") == "python"
    ])
    post_python_code = _extract_script([
        s for s in raw_postconditions
        if isinstance(s, dict) and s.get("kind") == "python"
    ])

    # Also support explicit setup_scripts/teardown_scripts keys
    setup_script = _extract_script(base.get("setup_scripts")) or pre_python_code
    teardown_script = _extract_script(base.get("teardown_scripts")) or post_python_code

    # --- API-call preconditions only (no python-only steps) ---
    engine_preconditions = []
    for step in raw_preconditions:
        if isinstance(step, dict) and step.get("kind") != "python":
            engine_preconditions.append(_convert_precondition(step))

    # Convert extracts
    extracts = base.get("extracts") or base.get("extract") or []
    engine_extracts = _convert_extracts(extracts) if extracts else []

    # Convert assertions
    raw_assertions = base.get("assertions") or []
    engine_assertions = _convert_assertions(raw_assertions)

    return {
        "title": title or iface.summary or f"{method} {path}",
        "interface": {
            "url": path,
            "method": method.lower(),
        },
        "headers": headers,
        "request": request_block,
        "setup_script": setup_script,
        "teardown_script": teardown_script,
        "preconditions": engine_preconditions,
        "extract": engine_extracts,
        "assertions": engine_assertions,
    }
