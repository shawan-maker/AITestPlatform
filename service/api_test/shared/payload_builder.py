from typing import Any


import re


def _normalize_template_vars(text):
    """Normalize template variables: {var} -> ${var} (engine only recognizes ${var})."""
    if not isinstance(text, str):
        return text
    return re.sub(r'(?<!\$)\{(\w+)\}', r'${\1}', text)


def _normalize_in_structure(obj):
    """Recursively normalize template variables in dicts/lists."""
    if isinstance(obj, str):
        return _normalize_template_vars(obj)
    elif isinstance(obj, dict):
        return {k: _normalize_in_structure(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_in_structure(item) for item in obj]
    return obj


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
        combined = "from ApiEngine.infra import global_func\n" + combined
    return combined


def _convert_precondition(step: dict) -> dict:
    """Convert a precondition step into ApiEngine format.

    Supports two input formats:
    - AI format: body in step.request.data/json, path in step.interface.url
    - Frontend format: body in step.body, path in step.path
    """
    iface = step.get("interface") or {}
    path = iface.get("url") or iface.get("path") or step.get("path", "")
    method = iface.get("method") or step.get("method") or "GET"
    headers = step.get("headers") or {}

    path = _normalize_template_vars(path)

    # Body: prefer request sub-object (AI), fallback to top-level body (frontend)
    req = step.get("request") or {}
    body = _normalize_in_structure(req.get("data") or req.get("json") or step.get("body") or {})
    query = _normalize_in_structure(req.get("params") or step.get("query") or step.get("params") or {})

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
        "setup_script": _normalize_template_vars(step.get("setup_script") or _extract_script(step.get("setup_scripts"))),
        "teardown_script": step.get("teardown_script") or _extract_script(step.get("teardown_scripts")),
    }

    # Extract: AI format already has {var_name, extract_expr}; frontend needs conversion
    extracts = step.get("extract") or step.get("extracts")
    if extracts and isinstance(extracts, list):
        if isinstance(extracts[0], dict) and "var_name" in extracts[0]:
            result["extract"] = extracts
        else:
            result["extract"] = _convert_extracts(extracts)

    # Assertions: AI format already has {type, field, expected}; frontend needs conversion
    assertions = step.get("assertions")
    if assertions and isinstance(assertions, list):
        if isinstance(assertions[0], dict) and "type" in assertions[0]:
            result["assertions"] = assertions
        else:
            result["assertions"] = _convert_assertions(assertions)

    # Nested preconditions (recursive)
    sub = step.get("preconditions")
    if sub and isinstance(sub, list):
        nested = [_convert_precondition(s) for s in sub if isinstance(s, dict) and s.get("kind") != "python"]
        if nested:
            result["preconditions"] = nested

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


def normalize_preconditions(preconditions: list, preconditions_api_doc: list) -> list:
    """根据接口文档修正 AI 生成的前置步骤的 Content-Type 和 body 字段。

    当 preconditions_api_doc 为空时，返回原始列表（由调用方补充文档后重试）。
    """
    if not preconditions:
        return preconditions
    if not preconditions_api_doc:
        print(f"[normalize] docs=0, 跳过 (preconditions={len(preconditions)})")
        return preconditions

    # 构建多种索引
    doc_by_summary: dict = {}
    doc_by_method_path: dict = {}
    for doc in preconditions_api_doc:
        summary = (doc.get("summary") or "").strip()
        if summary:
            doc_by_summary[summary] = doc
        method = (doc.get("method") or "").upper()
        path = doc.get("path") or ""
        if method and path:
            doc_by_method_path[f"{method} {path}"] = doc

    print(f"[normalize] summaries={list(doc_by_summary.keys())}, paths={list(doc_by_method_path.keys())}")

    def _find_doc(step: dict):
        title = (step.get("title") or "").strip()
        if title in doc_by_summary:
            return doc_by_summary[title]
        for summary, doc in doc_by_summary.items():
            if summary and summary in title:
                return doc
        for summary, doc in doc_by_summary.items():
            if title and title in summary:
                return doc
        iface = step.get("interface") or {}
        step_method = (iface.get("method") or "").upper()
        step_url = iface.get("url") or iface.get("path") or ""
        key = f"{step_method} {step_url}"
        if key in doc_by_method_path:
            return doc_by_method_path[key]
        for mp_key, doc in doc_by_method_path.items():
            if step_url and step_url in mp_key:
                return doc
        return None

    def _fix_step(step: dict):
        if not isinstance(step, dict):
            return
        title = (step.get("title") or "").strip()
        doc = _find_doc(step)
        if not doc:
            print(f"[normalize] 未匹配: title='{title}'")
            return

        request_body = doc.get("requestBody") or {}
        correct_ct = (request_body.get("content_type") or "").lower()
        if not correct_ct:
            print(f"[normalize] '{title}': 接口文档无 content_type, 跳过")
            return

        headers = step.get("headers") or {}
        request = step.get("request") or {}

        is_form = "form-urlencoded" in correct_ct or "multipart" in correct_ct
        current_ct = (headers.get("Content-Type") or "").lower()
        current_is_form = "form-urlencoded" in current_ct or "multipart" in current_ct

        if is_form and not current_is_form:
            headers["Content-Type"] = correct_ct or "application/x-www-form-urlencoded"
            if request.get("json") and not request.get("data"):
                request["data"] = request.pop("json")
            print(f"[normalize] 修正 '{title}': json→data, CT→{headers['Content-Type']}")
        elif not is_form and current_is_form:
            headers["Content-Type"] = "application/json"
            if request.get("data") and not request.get("json"):
                request["json"] = request.pop("data")
            print(f"[normalize] 修正 '{title}': data→json, CT→{headers['Content-Type']}")
        else:
            print(f"[normalize] '{title}' CT 已正确: {current_ct or '(未设置)'}")

        step["headers"] = headers
        step["request"] = request

        sub = step.get("preconditions")
        if sub and isinstance(sub, list):
            for s in sub:
                _fix_step(s)

    for step in preconditions:
        _fix_step(step)

    return preconditions


async def enrich_preconditions_api_doc(
    preconditions: list,
    project_id: int,
    existing_docs: list | None = None,
) -> list:
    """当 preconditions_api_doc 为空时，从数据库按前置步骤 title 查找接口文档。

    返回合并后的文档列表（existing_docs + 从 DB 补充的文档）。
    """
    if not preconditions:
        return existing_docs or []

    existing = list(existing_docs or [])
    existing_summaries = {
        (d.get("summary") or "").strip()
        for d in existing if isinstance(d, dict)
    }

    from service.api_test.interface.models import ApiInterface
    from service.api_test.shared.interface_doc import interface_to_doc_dict

    missing_titles = []
    for step in preconditions:
        if not isinstance(step, dict):
            continue
        title = (step.get("title") or "").strip()
        if title and title not in existing_summaries:
            missing_titles.append(title)

    if not missing_titles:
        return existing

    ifaces = await ApiInterface.filter(
        project_id=project_id,
        summary__in=missing_titles,
        is_current=True,
    )
    for iface in ifaces:
        doc = interface_to_doc_dict(iface)
        existing.append(doc)
        print(f"[enrich] 从 DB 补充接口文档: summary='{iface.summary}', "
              f"content_type='{(iface.request_body or {}).get('content_type')}'")

    return existing
