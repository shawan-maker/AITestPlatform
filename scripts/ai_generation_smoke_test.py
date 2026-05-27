"""AI 智能体中心 HTTP 联调脚本（canonical /api/v1/ai-generation/*）。

用法:
  FUNCTIONAL_GEN_MOCK=1 API_TEST_GEN_MOCK=1 python scripts/ai_generation_smoke_test.py
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("FUNCTIONAL_GEN_MOCK", "1")
os.environ.setdefault("API_TEST_GEN_MOCK", "1")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def _login(client: TestClient, username: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _poll_session(
    client: TestClient,
    headers: dict,
    url: str,
    *,
    timeout_sec: float = 15.0,
) -> dict:
    deadline = time.time() + timeout_sec
    data: dict = {}
    while time.time() < deadline:
        resp = client.get(url, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        if data.get("status") in {"success", "failed"}:
            return data
        time.sleep(0.3)
    return data


def _run(client: TestClient) -> None:
    token = _login(client, "admin", "123456")
    headers = _auth_headers(token)

    meta = client.get("/api/v1/ai-generation/meta", headers=headers)
    assert meta.status_code == 200, meta.text
    assert meta.json()["data"]["single_interface_only"] is True
    print("meta ok")

    project_name = f"AIGenSmoke_{int(time.time())}"
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": project_name, "description": "ai generation smoke"},
        headers=headers,
    )
    assert proj_resp.status_code == 200, proj_resp.text
    project_id = proj_resp.json()["data"]["id"]

    func_resp = client.post(
        "/api/v1/ai-generation/functional/generate",
        json={
            "project_id": project_id,
            "requirement_text": "用户登录与权限校验",
        },
        headers=headers,
    )
    assert func_resp.status_code == 200, func_resp.text
    func_session_id = func_resp.json()["data"]["id"]
    func_session = _poll_session(
        client,
        headers,
        f"/api/v1/ai-generation/functional/sessions/{func_session_id}",
    )
    assert func_session["status"] == "success", func_session.get("error_message")
    print("functional generate ok", func_session_id)

    cat_resp = client.post(
        f"/api/v1/api-test/catalogs?project_id={project_id}",
        headers=headers,
        json={"name": "ai-smoke-catalog"},
    )
    assert cat_resp.status_code == 200, cat_resp.text
    catalog_id = cat_resp.json()["data"]["id"]

    iface_resp = client.post(
        "/api/v1/api-test/interfaces",
        headers=headers,
        json={
            "project_id": project_id,
            "catalog_id": catalog_id,
            "method": "GET",
            "path": "/ai-smoke/ping",
            "summary": "ai smoke ping",
            "parameters": {"header": [], "path": [], "query": []},
            "responses": [],
        },
    )
    assert iface_resp.status_code == 200, iface_resp.text
    interface_id = iface_resp.json()["data"]["id"]

    api_preview = client.post(
        "/api/v1/ai-generation/api/generate-from-interface",
        headers=headers,
        json={"interface_id": interface_id, "user_prompt": "smoke"},
    )
    assert api_preview.status_code == 200, api_preview.text
    api_session_id = api_preview.json()["data"]["session_id"]
    base_cases = api_preview.json()["data"]["base_cases"]
    assert base_cases, "mock 预览应返回基础用例"
    print("api preview ok", api_session_id)

    api_session = client.get(
        f"/api/v1/ai-generation/api/sessions/{api_session_id}",
        headers=headers,
    )
    assert api_session.status_code == 200, api_session.text

    envs = client.get(
        f"/api/v1/env/environments?project_id={project_id}",
        headers=headers,
    )
    if envs.status_code == 200 and envs.json()["data"]["items"]:
        environment_id = envs.json()["data"]["items"][0]["id"]
        selected = list(range(min(1, len(base_cases))))
        confirm = client.post(
            "/api/v1/ai-generation/api/confirm",
            headers=headers,
            json={
                "session_id": api_session_id,
                "selected_indexes": selected,
                "environment_id": environment_id,
                "interface_id": interface_id,
            },
        )
        assert confirm.status_code == 200, confirm.text
        print("api confirm ok")

    client.delete(f"/api/v1/api-test/interfaces/{interface_id}", headers=headers)
    client.delete(f"/api/v1/api-test/catalogs/{catalog_id}", headers=headers)
    print("ai_generation_smoke_test: OK")


if __name__ == "__main__":
    with TestClient(app) as client:
        _run(client)
