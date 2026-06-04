"""知识库模块 Phase B/C/D 联调脚本。用法: python scripts/knowledge_smoke_test.py

规则说明见 service/knowledge/README.md
"""

import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

_TERMINAL_INDEX_STATUSES = {"indexed", "failed", "na"}
_TERMINAL_PARSE_STATUSES = {"parsed", "failed"}


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
    timeout_sec: float = 60.0,
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
        if last_status in _TERMINAL_INDEX_STATUSES:
            return last_status
        time.sleep(interval_sec)
    return last_status


def _poll_api_doc_parsed(
    client: TestClient,
    headers: dict,
    document_id: int,
    *,
    timeout_sec: float = 60.0,
    interval_sec: float = 0.5,
) -> dict:
    deadline = time.time() + timeout_sec
    last_detail: dict = {}
    while time.time() < deadline:
        detail_resp = client.get(
            f"/api/v1/knowledge/documents/{document_id}",
            headers=headers,
        )
        assert detail_resp.status_code == 200, detail_resp.text
        last_detail = detail_resp.json()["data"]
        parse_status = last_detail.get("parse_status") or ""
        if parse_status in _TERMINAL_PARSE_STATUSES:
            return last_detail
        time.sleep(interval_sec)
    return last_detail


def _assert_save_flags(
    detail: dict,
    *,
    can_save_requirement: bool | None = None,
    requirement_saved: bool | None = None,
    can_save_interfaces: bool | None = None,
    interfaces_saved: bool | None = None,
    min_parsed_interfaces: int | None = None,
) -> None:
    if can_save_requirement is not None:
        assert detail.get("can_save_requirement") is can_save_requirement, detail
    if requirement_saved is not None:
        assert detail.get("requirement_saved") is requirement_saved, detail
    if can_save_interfaces is not None:
        assert detail.get("can_save_interfaces") is can_save_interfaces, detail
    if interfaces_saved is not None:
        assert detail.get("interfaces_saved") is interfaces_saved, detail
    if min_parsed_interfaces is not None:
        parsed = detail.get("parsed_interfaces") or []
        assert len(parsed) >= min_parsed_interfaces, detail


_MINIMAL_SWAGGER = {
    "swagger": "2.0",
    "info": {"title": "t", "version": "1.0"},
    "paths": {
        "/ping": {
            "get": {
                "tags": ["Health"],
                "summary": "ping",
                "parameters": [
                    {
                        "name": "verbose",
                        "in": "query",
                        "type": "boolean",
                        "required": False,
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}


def _test_swagger_pisces_parse_display() -> None:
    """swagger_pisces.json：parse + display 字段可计算（不依赖 DB）。"""
    from service.knowledge.document.parse_display import to_parsed_interface_item
    from service.knowledge.document.parsed_interface_service import items_from_raw_list
    from utils.parser.swagger_document_parser import parse_swagger_file

    pisces_path = ROOT / "test_data" / "files" / "5" / "swagger_pisces.json"
    assert pisces_path.is_file(), pisces_path

    raw_items = parse_swagger_file(pisces_path)
    assert len(raw_items) == 3, len(raw_items)
    for raw in raw_items:
        assert raw.get("tags"), raw
        display = to_parsed_interface_item(raw)
        assert display.get("request_modules"), display
        assert display.get("api_path"), display

    cached_path = ROOT / "rag" / "parsed" / "5" / "117" / "v1.2" / "parsed.json"
    if cached_path.is_file():
        cached = json.loads(cached_path.read_text(encoding="utf-8"))
        recovered = items_from_raw_list(cached)
        assert len(recovered) == 3, recovered
        for item in recovered:
            dumped = item.model_dump()
            assert dumped.get("request_modules"), dumped
            assert dumped.get("api_path"), dumped
    print("swagger_pisces parse/display ok")


def _run_swagger_pisces_upload(
    client: TestClient,
    headers: dict,
    project_id: int,
    module_id: int,
) -> None:
    pisces_path = ROOT / "test_data" / "files" / "5" / "swagger_pisces.json"
    if not pisces_path.is_file():
        print("swagger_pisces.json missing, skip upload test")
        return

    content = pisces_path.read_bytes()
    upload_resp = client.post(
        f"/api/v1/knowledge/documents?project_id={project_id}",
        data={
            "title": "swagger_pisces_smoke",
            "doc_type": "api_doc",
            "parse_mode": "swagger",
            "module_id": str(module_id),
        },
        files={
            "file": (
                "swagger_pisces.json",
                io.BytesIO(content),
                "application/json",
            )
        },
        headers=headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    doc_id = upload_resp.json()["data"]["id"]
    detail = _poll_api_doc_parsed(client, headers, doc_id)
    assert detail.get("parse_status") == "parsed", detail
    _assert_save_flags(
        detail,
        can_save_interfaces=True,
        interfaces_saved=False,
        min_parsed_interfaces=3,
    )
    parsed = detail.get("parsed_interfaces") or []
    assert len(parsed) >= 3, detail
    body_item = next(
        (i for i in parsed if i.get("path") == "/inner/v1/orders/callback"),
        None,
    )
    assert body_item is not None, parsed
    assert body_item.get("request_modules"), body_item
    assert body_item.get("api_path"), body_item
    assert "effectiveTime" in (body_item.get("request_modules") or ""), body_item

    version_id = (detail.get("current_version") or {}).get("id") or detail.get(
        "current_version_id"
    )
    assert version_id, detail
    parsed_api = client.get(
        f"/api/v1/knowledge/documents/{doc_id}/versions/{version_id}/parsed-interfaces",
        headers=headers,
    )
    assert parsed_api.status_code == 200, parsed_api.text
    api_items = parsed_api.json()["data"]["items"]
    assert len(api_items) >= 3, api_items
    assert api_items[0].get("request_modules"), api_items[0]

    client.delete(f"/api/v1/knowledge/documents/{doc_id}", headers=headers)
    print("swagger_pisces upload/detail ok")


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

    detail = _poll_api_doc_parsed(client, headers, api_doc_id)
    print("api doc parse status", detail.get("parse_status"))
    if detail.get("parse_status") == "failed":
        print("api doc parse failed, skip import test")
        return

    _assert_save_flags(
        detail,
        can_save_interfaces=True,
        interfaces_saved=False,
        min_parsed_interfaces=1,
    )
    print("api doc save flags before import ok")

    version = detail.get("current_version") or {}
    version_id = version.get("id")
    assert version_id, "missing current version for api doc"

    parsed_api = client.get(
        f"/api/v1/knowledge/documents/{api_doc_id}/versions/{version_id}/parsed-interfaces",
        headers=headers,
    )
    assert parsed_api.status_code == 200, parsed_api.text
    parsed_items = parsed_api.json()["data"]["items"]
    assert len(parsed_items) >= 1
    first_parsed = parsed_items[0]
    assert first_parsed.get("method") == "GET"
    assert first_parsed.get("api_path") == "Health"
    assert "query" in (first_parsed.get("request_modules") or "")
    print("parsed-interfaces api ok")

    from service.core.config import BASE_DIR, KNOWLEDGE_PARSE_ROOT

    version_label = detail.get("version_label") or version.get("version_label") or "v1.0"
    parse_dir = KNOWLEDGE_PARSE_ROOT / str(project_id) / str(api_doc_id) / version_label
    parse_dir.mkdir(parents=True, exist_ok=True)
    slim_path = parse_dir / "parsed.json"
    slim_path.write_text(
        json.dumps(
            [{"method": "GET", "path": "/ping", "summary": "slim-only"}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rel_path = str(slim_path.relative_to(BASE_DIR))
    print("slim parsed.json written", rel_path)

    slim_recover_resp = client.get(
        f"/api/v1/knowledge/documents/{api_doc_id}/versions/{version_id}/parsed-interfaces",
        headers=headers,
    )
    assert slim_recover_resp.status_code == 200, slim_recover_resp.text
    slim_items = slim_recover_resp.json()["data"]["items"]
    assert len(slim_items) >= 1, slim_items
    slim_first = slim_items[0]
    assert slim_first.get("request_modules"), slim_first
    assert slim_first.get("api_path"), slim_first
    print("slim json recovery ok", slim_first.get("request_modules"), slim_first.get("api_path"))

    list_resp = client.get(
        f"/api/v1/knowledge/documents?project_id={project_id}&title=demo-swagger",
        headers=headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    list_items = list_resp.json()["data"]["items"]
    api_row = next((i for i in list_items if i["id"] == api_doc_id), None)
    assert api_row is not None, list_items
    assert api_row.get("can_save_interfaces") is True, api_row
    print("list save flags ok")

    preview_resp = client.post(
        f"/api/v1/knowledge/documents/{api_doc_id}/versions/{version_id}/import-interfaces/preview",
        headers=headers,
    )
    assert preview_resp.status_code == 200, preview_resp.text
    preview_items = preview_resp.json()["data"]["items"]
    assert len(preview_items) >= 1, preview_items
    print("import preview ok", len(preview_items))

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

    after_import_resp = client.get(
        f"/api/v1/knowledge/documents/{api_doc_id}",
        headers=headers,
    )
    assert after_import_resp.status_code == 200, after_import_resp.text
    after_import = after_import_resp.json()["data"]
    _assert_save_flags(
        after_import,
        can_save_interfaces=False,
        interfaces_saved=True,
    )
    print("api doc save flags after import ok")

    saved_iface = (after_import.get("parsed_interfaces") or [None])[0]
    assert saved_iface is not None, after_import
    assert saved_iface.get("catalog_path"), saved_iface
    assert saved_iface.get("module_name"), saved_iface
    assert saved_iface.get("request_modules"), saved_iface
    assert saved_iface.get("api_path"), saved_iface
    print(
        "saved interface fields ok",
        saved_iface.get("request_modules"),
        saved_iface.get("api_path"),
    )

    rev_api = client.post(
        f"/api/v1/knowledge/documents/{api_doc_id}/versions",
        files={
            "file": (
                "demo-swagger-v2.json",
                io.BytesIO(swagger_bytes),
                "application/json",
            )
        },
        headers=headers,
    )
    assert rev_api.status_code == 200, rev_api.text
    assert rev_api.json()["data"]["version_label"] == "v1.1"
    deadline = time.time() + 60.0
    detail_v2 = detail
    while time.time() < deadline:
        detail_v2 = client.get(
            f"/api/v1/knowledge/documents/{api_doc_id}",
            headers=headers,
        ).json()["data"]
        if (
            detail_v2.get("version_label") == "v1.1"
            and detail_v2.get("can_save_interfaces") is True
        ):
            break
        time.sleep(0.5)
    _assert_save_flags(
        detail_v2,
        can_save_interfaces=True,
        interfaces_saved=False,
    )
    print("api doc reupload save flags ok")

    del_api_resp = client.delete(
        f"/api/v1/knowledge/documents/{api_doc_id}",
        headers=headers,
    )
    assert del_api_resp.status_code == 200, del_api_resp.text
    print("api doc delete ok")


def _run_phase_d_api_ai_mode_spec(
    client: TestClient,
    headers: dict,
    project_id: int,
    module_id: int,
) -> None:
    """parse_mode=ai 但内容为 Swagger 时仍应结构化解析并出现保存接口按钮。"""
    swagger_bytes = json.dumps(_MINIMAL_SWAGGER, ensure_ascii=False).encode("utf-8")
    upload_resp = client.post(
        f"/api/v1/knowledge/documents?project_id={project_id}",
        data={
            "title": "demo-swagger-ai.json",
            "doc_type": "api_doc",
            "parse_mode": "ai",
            "module_id": str(module_id),
        },
        files={
            "file": (
                "demo-swagger-ai.json",
                io.BytesIO(swagger_bytes),
                "application/json",
            )
        },
        headers=headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    doc_id = upload_resp.json()["data"]["id"]
    detail = _poll_api_doc_parsed(client, headers, doc_id)
    assert detail.get("parse_status") == "parsed", detail
    _assert_save_flags(detail, can_save_interfaces=True, interfaces_saved=False)
    client.delete(f"/api/v1/knowledge/documents/{doc_id}", headers=headers)
    print("api doc ai mode spec parse ok")


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
        f"/api/v1/knowledge/documents?project_id={project_id}&title=demo-req",
        headers=headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["data"]["total"] >= 1
    print("list title filter ok")

    index_status = _poll_index_status(client, headers, document_id)
    print("index status", index_status)
    assert index_status in _TERMINAL_INDEX_STATUSES | {"pending"}, (
        f"unexpected index_status: {index_status}"
    )

    detail_resp = client.get(
        f"/api/v1/knowledge/documents/{document_id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()["data"]
    assert detail.get("module_name")
    print("detail ok")

    version_id = (detail.get("current_version") or {}).get("id")

    if index_status == "indexed" and version_id:
        _assert_save_flags(
            detail,
            can_save_requirement=True,
            requirement_saved=False,
        )
        print("requirement save flags before confirm ok")

        list_before = client.get(
            f"/api/v1/knowledge/documents?project_id={project_id}&title=demo-req",
            headers=headers,
        )
        assert list_before.status_code == 200, list_before.text
        req_row = next(
            (i for i in list_before.json()["data"]["items"] if i["id"] == document_id),
            None,
        )
        assert req_row is not None, list_before.json()
        assert req_row.get("can_save_requirement") is True, req_row
        print("list requirement save flags ok")

        cand_api = client.get(
            f"/api/v1/knowledge/documents/{document_id}/requirement-candidate",
            headers=headers,
        )
        assert cand_api.status_code == 200, cand_api.text
        cand = cand_api.json()["data"]
        assert cand is not None, "expected requirement candidate"
        assert cand["title"] == "demo-req.md_v1.0", cand
        print("requirement-candidate api ok", cand["id"])

        preview_resp = client.get(
            f"/api/v1/knowledge/documents/{document_id}/versions/{version_id}/text-preview",
            headers=headers,
        )
        assert preview_resp.status_code == 200, preview_resp.text
        assert b"demo requirement" in preview_resp.json()["data"]["text"].encode()
        print("text-preview ok")

        confirm_resp = client.post(
            f"/api/v1/functional/requirements/candidates/{cand['id']}/confirm",
            json={"direct_save": True, "module_id": module_id},
            headers=headers,
        )
        assert confirm_resp.status_code == 200, confirm_resp.text
        print("candidate confirm ok")

        after_confirm_resp = client.get(
            f"/api/v1/knowledge/documents/{document_id}",
            headers=headers,
        )
        assert after_confirm_resp.status_code == 200, after_confirm_resp.text
        after_confirm = after_confirm_resp.json()["data"]
        _assert_save_flags(
            after_confirm,
            can_save_requirement=False,
            requirement_saved=True,
        )
        print("requirement save flags after confirm ok")

        cand_after = client.get(
            f"/api/v1/knowledge/documents/{document_id}/requirement-candidate",
            headers=headers,
        )
        assert cand_after.status_code == 200, cand_after.text
        assert cand_after.json()["data"] is None
        print("requirement-candidate cleared after confirm ok")

        dup_upload = client.post(
            f"/api/v1/knowledge/documents?project_id={project_id}",
            data={
                "title": "demo-req-copy.md",
                "doc_type": "requirement",
                "parse_mode": "ai",
                "module_id": str(module_id),
            },
            files={"file": ("demo-req-copy.md", io.BytesIO(content), "text/markdown")},
            headers=headers,
        )
        assert dup_upload.status_code == 200, dup_upload.text
        dup_id = dup_upload.json()["data"]["id"]
        _poll_index_status(client, headers, dup_id)
        dup_cand = client.get(
            f"/api/v1/knowledge/documents/{dup_id}/requirement-candidate",
            headers=headers,
        ).json()["data"]
        if dup_cand:
            confirm_copy = client.post(
                f"/api/v1/functional/requirements/candidates/{dup_cand['id']}/confirm",
                json={"direct_save": True, "title": "demo-req.md", "module_id": module_id},
                headers=headers,
            )
            assert confirm_copy.status_code == 200, confirm_copy.text
            title = confirm_copy.json()["data"]["title"]
            assert title.startswith("demo-req") and "_copy" in title, title
            print("title _copy ok", title)
            client.delete(f"/api/v1/knowledge/documents/{dup_id}", headers=headers)

    _run_phase_d_api_import(client, headers, project_id, module_id)
    _run_swagger_pisces_upload(client, headers, project_id, module_id)
    _run_phase_d_api_ai_mode_spec(client, headers, project_id, module_id)

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
    _poll_index_status(client, headers, document_id)

    after_reupload_resp = client.get(
        f"/api/v1/knowledge/documents/{document_id}",
        headers=headers,
    )
    assert after_reupload_resp.status_code == 200, after_reupload_resp.text
    after_reupload = after_reupload_resp.json()["data"]
    _assert_save_flags(
        after_reupload,
        can_save_requirement=True,
        requirement_saved=False,
    )
    print("requirement reupload save flags ok")

    del_resp = client.delete(
        f"/api/v1/knowledge/documents/{document_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200, del_resp.text
    print("delete ok")
    print("ALL PASSED")


if __name__ == "__main__":
    _test_swagger_pisces_parse_display()
    with TestClient(app) as client:
        _run(client)
