import json
from typing import Any


def interface_to_doc_dict(iface) -> dict[str, Any]:
    return {
        "method": iface.method,
        "path": iface.path,
        "summary": iface.summary,
        "parameters": iface.parameters or {"header": [], "path": [], "query": []},
        "requestBody": iface.request_body,
        "responses": iface.responses or [],
    }


def interface_to_doc_json(iface) -> str:
    return json.dumps(interface_to_doc_dict(iface), ensure_ascii=False)
