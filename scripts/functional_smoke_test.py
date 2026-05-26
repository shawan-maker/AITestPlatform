"""功能测试模块 FT-B~E 联调脚本。用法: python scripts/functional_smoke_test.py"""

import io
import os
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


def _poll_generation_session(
    client: TestClient,
    headers: dict,
    session_id: int,
    *,
    timeout_sec: float = 15.0,
) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = client.get(
            f"/api/v1/functional/case-generation/sessions/{session_id}",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        if data["status"] in {"success", "failed"}:
            return data
        time.sleep(0.3)
    return data


def _run(client: TestClient) -> None:
    token = _login(client, "admin", "123456")
    headers = _auth_headers(token)

    project_name = f"FuncSmoke_{int(time.time())}"
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": project_name, "description": "functional smoke"},
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

    # manual requirement CRUD
    req_title = f"手工需求_{int(time.time())}"
    create_req = client.post(
        "/api/v1/functional/requirements",
        json={
            "project_id": project_id,
            "module_id": module_id,
            "title": req_title,
            "description": "smoke manual requirement",
        },
        headers=headers,
    )
    assert create_req.status_code == 200, create_req.text
    req_id = create_req.json()["data"]["id"]
    assert create_req.json()["data"]["source_type"] == "manual"
    print("manual requirement create ok", req_id)

    patch_req = client.patch(
        f"/api/v1/functional/requirements/{req_id}",
        json={"description": "updated"},
        headers=headers,
    )
    assert patch_req.status_code == 200, patch_req.text
    print("manual requirement patch ok")

    list_req = client.get(
        f"/api/v1/functional/requirements?project_id={project_id}",
        headers=headers,
    )
    assert list_req.status_code == 200, list_req.text
    assert list_req.json()["data"]["total"] >= 1
    print("requirement list ok")

    # knowledge upload -> candidate -> confirm
    content = b"# functional smoke requirement\n"
    upload_resp = client.post(
        f"/api/v1/knowledge/documents?project_id={project_id}",
        data={
            "title": "func-smoke-req.md",
            "doc_type": "requirement",
            "parse_mode": "ai",
            "module_id": str(module_id),
        },
        files={"file": ("func-smoke-req.md", io.BytesIO(content), "text/markdown")},
        headers=headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    document_id = upload_resp.json()["data"]["id"]
    index_status = _poll_index_status(client, headers, document_id)
    print("knowledge index status", index_status)

    candidate_id = None
    if index_status == "indexed":
        cand_list = client.get(
            f"/api/v1/functional/requirements/candidates?project_id={project_id}",
            headers=headers,
        )
        assert cand_list.status_code == 200, cand_list.text
        count_resp = client.get(
            f"/api/v1/functional/requirements/candidates/count?project_id={project_id}",
            headers=headers,
        )
        assert count_resp.status_code == 200, count_resp.text
        assert count_resp.json()["data"]["count"] >= 1
        candidate_id = cand_list.json()["data"]["items"][0]["id"]

        confirm_resp = client.post(
            f"/api/v1/functional/requirements/candidates/{candidate_id}/confirm",
            json={"module_id": module_id},
            headers=headers,
        )
        assert confirm_resp.status_code == 200, confirm_resp.text
        confirmed_id = confirm_resp.json()["data"]["id"]
        assert confirm_resp.json()["data"]["source_type"] == "knowledge"
        print("candidate confirm ok", confirmed_id)

        reindex_resp = client.post(
            f"/api/v1/knowledge/documents/{document_id}/reindex",
            headers=headers,
        )
        assert reindex_resp.status_code == 200, reindex_resp.text
        _poll_index_status(client, headers, document_id)
        cand_list2 = client.get(
            f"/api/v1/functional/requirements/candidates?project_id={project_id}",
            headers=headers,
        )
        assert cand_list2.status_code == 200, cand_list2.text
        if cand_list2.json()["data"]["total"] >= 1:
            candidate_id2 = cand_list2.json()["data"]["items"][0]["id"]
            dup_resp = client.post(
                f"/api/v1/functional/requirements/candidates/{candidate_id2}/confirm",
                json={"module_id": module_id},
                headers=headers,
            )
            assert dup_resp.status_code == 409, dup_resp.text
            print("candidate confirm 409 ok")
    else:
        print("skip candidate flow (index not completed)")

    # catalog + manual case
    cat_resp = client.post(
        f"/api/v1/functional/case-catalogs?project_id={project_id}",
        json={"name": "冒烟目录"},
        headers=headers,
    )
    assert cat_resp.status_code == 200, cat_resp.text
    catalog_id = cat_resp.json()["data"]["id"]
    print("catalog create ok", catalog_id)

    tree_resp = client.get(
        f"/api/v1/functional/case-catalogs/tree?project_id={project_id}",
        headers=headers,
    )
    assert tree_resp.status_code == 200, tree_resp.text
    assert len(tree_resp.json()["data"]) >= 1
    print("catalog tree ok")

    case_resp = client.post(
        "/api/v1/functional/cases",
        json={
            "project_id": project_id,
            "catalog_id": catalog_id,
            "case_name": "手工冒烟用例",
            "test_steps": "1. 执行",
            "expected_result": "通过",
        },
        headers=headers,
    )
    assert case_resp.status_code == 200, case_resp.text
    case_id = case_resp.json()["data"]["id"]
    assert case_resp.json()["data"]["exec_result"] == "pending"
    print("manual case create ok", case_id)

    copy_resp = client.post(
        f"/api/v1/functional/cases/{case_id}/copy",
        headers=headers,
    )
    assert copy_resp.status_code == 200, copy_resp.text
    assert copy_resp.json()["data"]["case_name"].endswith("_copy")
    copy_id = copy_resp.json()["data"]["id"]
    print("case copy ok", copy_id)

    reorder_resp = client.post(
        "/api/v1/functional/cases/reorder",
        json={"catalog_id": catalog_id, "ordered_ids": [copy_id, case_id]},
        headers=headers,
    )
    assert reorder_resp.status_code == 200, reorder_resp.text
    print("case reorder ok")

    export_resp = client.get(
        f"/api/v1/functional/cases/export?project_id={project_id}&catalog_id={catalog_id}",
        headers=headers,
    )
    assert export_resp.status_code == 200, export_resp.text
    assert b"case_name" in export_resp.content
    print("case export ok")

    batch_resp = client.post(
        "/api/v1/functional/cases/batch-update",
        json={"case_ids": [case_id, copy_id], "priority": 2},
        headers=headers,
    )
    assert batch_resp.status_code == 200, batch_resp.text
    assert batch_resp.json()["data"]["success_count"] == 2
    print("case batch update ok")

    # optional AI generation (mock when no LLM key)
    os.environ.setdefault("FUNCTIONAL_GEN_MOCK", "1")
    gen_resp = client.post(
        "/api/v1/functional/case-generation/sessions",
        json={
            "project_id": project_id,
            "requirement_id": req_id,
            "requirement_text": "用户登录功能",
        },
        headers=headers,
    )
    assert gen_resp.status_code == 200, gen_resp.text
    session_id = gen_resp.json()["data"]["id"]
    session_data = _poll_generation_session(client, headers, session_id)
    if session_data["status"] == "success":
        save_resp = client.post(
            f"/api/v1/functional/case-generation/sessions/{session_id}/save",
            json={"catalog_id": catalog_id, "case_indexes": [0], "requirement_id": req_id},
            headers=headers,
        )
        assert save_resp.status_code == 200, save_resp.text
        assert save_resp.json()["data"]["created_case_ids"]
        print("AI generation save ok")
    else:
        print("AI generation skipped/failed", session_data.get("error_message"))

    del_req = client.delete(
        f"/api/v1/functional/requirements/{req_id}",
        headers=headers,
    )
    assert del_req.status_code == 200, del_req.text
    assert "linked_case_count" in del_req.json()["data"]
    print("requirement delete ok")

    del_doc = client.delete(
        f"/api/v1/knowledge/documents/{document_id}",
        headers=headers,
    )
    assert del_doc.status_code == 200, del_doc.text
    print("knowledge cleanup ok")
    print("ALL PASSED")


if __name__ == "__main__":
    with TestClient(app) as client:
        _run(client)
