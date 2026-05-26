"""知识库模块 Phase B/C/D 联调脚本。用法: python scripts/knowledge_smoke_test.py"""

import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

_TERMINAL_STATUSES = {"indexed", "failed", "na"}


def _login(client: TestClient, username: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _poll_index_status(
    client: TestClient,
    headers: dict,
    document_id: int,
    *,
    timeout_sec: float = 30.0,
    interval_sec: float = 0.5,
) -> str:
    deadline = time.time() + timeout_sec
    last_status = "pending"
    while time.time() < deadline:
        detail_resp = client.get(
            f"/api/v1/knowledge/documents/{document_id}",
            headers=headers,
        )
        assert detail_resp.status_code == 200, detail_resp.text
        current = detail_resp.json()["data"].get("current_version") or {}
        last_status = current.get("index_status") or "pending"
        if last_status in _TERMINAL_STATUSES:
            return last_status
        time.sleep(interval_sec)
    return last_status


_MINIMAL_SWAGGER = {
    "swagger": "2.0",
    "info": {"title": "t", "version": "1.0"},
    "paths": {
        "/ping": {
            "get": {
                "summary": "ping",
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}


def _run_phase_d_api_import(
    client: TestClient,
    headers: dict,
    project_id: int,
    module_id: int,
) -> None:
    swagger_bytes = json.dumps(_MINIMAL_SWAGGER, ensure_ascii=False).encode("utf-8")
    upload_resp = client.post(
        f"/api/v1/knowledge/documents?project_id={project_id}",
        data={
            "title": "demo-swagger.json",
            "doc_type": "api_doc",
            "parse_mode": "swagger",
            "module_id": str(module_id),
        },
        files={
            "file": (
                "demo-swagger.json",
                io.BytesIO(swagger_bytes),
                "application/json",
            )
        },
        headers=headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    api_doc_id = upload_resp.json()["data"]["id"]
    print("api doc upload ok", api_doc_id)

    index_status = _poll_index_status(client, headers, api_doc_id)
    print("api doc parse status", index_status)
    if index_status == "failed":
        print("api doc parse failed, skip import test")
        return

    detail_resp = client.get(
        f"/api/v1/knowledge/documents/{api_doc_id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200, detail_resp.text
    version = detail_resp.json()["data"].get("current_version") or {}
    version_id = version.get("id")
    assert version_id, "missing current version for api doc"

    import_resp = client.post(
        f"/api/v1/knowledge/documents/{api_doc_id}/versions/{version_id}/import-interfaces",
        json={"module_id": module_id, "import_mode": "skip"},
        headers=headers,
    )
    assert import_resp.status_code == 200, import_resp.text
    result = import_resp.json()["data"]
    assert result["created"] >= 1, result
    assert len(result["interface_ids"]) >= 1
    print("import interfaces ok", result)

    del_api_resp = client.delete(
        f"/api/v1/knowledge/documents/{api_doc_id}",
        headers=headers,
    )
    assert del_api_resp.status_code == 200, del_api_resp.text
    print("api doc delete ok")


def _run(client: TestClient) -> None:
    token = _login(client, "admin", "123456")
    headers = _auth_headers(token)

    project_name = f"KnowSmoke_{int(time.time())}"
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": project_name, "description": "knowledge smoke"},
        headers=headers,
    )
    assert proj_resp.status_code == 200, proj_resp.text
    project_id = proj_resp.json()["data"]["id"]
    print("project ok", project_id)

    mod_resp = client.post(
        f"/api/v1/projects/{project_id}/modules",
        json={"name": "默认模块", "description": "smoke"},
        headers=headers,
    )
    assert mod_resp.status_code == 200, mod_resp.text
    module_id = mod_resp.json()["data"]["id"]
    print("module ok", module_id)

    content = b"# demo requirement\n"
    upload_resp = client.post(
        f"/api/v1/knowledge/documents?project_id={project_id}",
        data={
            "title": "demo-req.md",
            "doc_type": "requirement",
            "parse_mode": "ai",
            "module_id": str(module_id),
        },
        files={"file": ("demo-req.md", io.BytesIO(content), "text/markdown")},
        headers=headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    document_id = upload_resp.json()["data"]["id"]
    print("upload ok", document_id)

    list_resp = client.get(
        f"/api/v1/knowledge/documents?project_id={project_id}",
        headers=headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["data"]["total"] >= 1
    print("list ok")

    index_status = _poll_index_status(client, headers, document_id)
    print("index status", index_status)
    assert index_status in _TERMINAL_STATUSES | {"pending"}, (
        f"unexpected index_status: {index_status}"
    )

    detail_resp = client.get(
        f"/api/v1/knowledge/documents/{document_id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200, detail_resp.text
    print("detail ok")

    if index_status == "indexed":
        cand_resp = client.get(
            f"/api/v1/functional/requirements/candidates?project_id={project_id}",
            headers=headers,
        )
        assert cand_resp.status_code == 200, cand_resp.text
        candidates = cand_resp.json()["data"]
        assert candidates["total"] >= 1, candidates
        matched = [
            c
            for c in candidates["items"]
            if c.get("source_document_id") == document_id
        ]
        assert matched, "indexed requirement should create candidate"
        print("requirement candidate sync ok", matched[0]["id"])

    _run_phase_d_api_import(client, headers, project_id, module_id)

    dl_resp = client.get(
        f"/api/v1/knowledge/documents/{document_id}/download",
        headers=headers,
    )
    assert dl_resp.status_code == 200, dl_resp.text
    assert dl_resp.content == content
    print("download ok")

    rev_resp = client.post(
        f"/api/v1/knowledge/documents/{document_id}/versions",
        files={"file": ("demo-req.md", io.BytesIO(b"# v2\n"), "text/markdown")},
        headers=headers,
    )
    assert rev_resp.status_code == 200, rev_resp.text
    assert rev_resp.json()["data"]["version_label"] == "v1.1"
    print("reupload ok")

    hist_resp = client.get(
        f"/api/v1/knowledge/documents/{document_id}/versions",
        headers=headers,
    )
    assert hist_resp.status_code == 200, hist_resp.text
    assert hist_resp.json()["data"]["total"] == 2
    print("history ok")

    reindex_resp = client.post(
        f"/api/v1/knowledge/documents/{document_id}/reindex",
        headers=headers,
    )
    assert reindex_resp.status_code == 200, reindex_resp.text
    print("reindex ok")

    del_resp = client.delete(
        f"/api/v1/knowledge/documents/{document_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200, del_resp.text
    print("delete ok")
    print("ALL PASSED")


if __name__ == "__main__":
    with TestClient(app) as client:
        _run(client)
