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


def _consume_sse(resp) -> list[str]:
    assert resp.status_code == 200, resp.text
    chunks: list[str] = []
    for line in resp.iter_lines():
        if line:
            chunks.append(line.decode() if isinstance(line, bytes) else line)
    return chunks


def _run(client: TestClient) -> None:
    token = _login(client, "admin", "123456")
    headers = _auth_headers(token)

    meta = client.get("/api/v1/ai-generation/meta", headers=headers)
    assert meta.status_code == 200, meta.text
    assert meta.json()["data"]["single_interface_only"] is True
    assert meta.json()["data"]["history_limit"] >= 1
    print("meta ok")

    project_name = f"AIGenSmoke_{int(time.time())}"
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": project_name, "description": "ai generation smoke"},
        headers=headers,
    )
    assert proj_resp.status_code == 200, proj_resp.text
    project_id = proj_resp.json()["data"]["id"]

    func_session_resp = client.post(
        "/api/v1/ai-generation/functional/sessions",
        json={
            "project_id": project_id,
            "requirement_text": "用户登录与权限校验",
            "title": "登录用例",
        },
        headers=headers,
    )
    assert func_session_resp.status_code == 200, func_session_resp.text
    func_session_id = func_session_resp.json()["data"]["id"]

    sse_resp = client.post(
        f"/api/v1/ai-generation/functional/sessions/{func_session_id}/messages",
        json={"content": "请生成功能用例"},
        headers=headers,
    )
    func_chunks = _consume_sse(sse_resp)
    assert any("event: done" in c for c in func_chunks), func_chunks

    func_session = client.get(
        f"/api/v1/ai-generation/functional/sessions/{func_session_id}",
        headers=headers,
    )
    assert func_session.status_code == 200, func_session.text
    assert func_session.json()["data"]["status"] == "success"
    print("functional session + SSE ok", func_session_id)

    func_msgs = client.get(
        f"/api/v1/ai-generation/functional/sessions/{func_session_id}/messages",
        headers=headers,
    )
    assert func_msgs.status_code == 200, func_msgs.text
    assert len(func_msgs.json()["data"]) >= 2

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

    api_session_resp = client.post(
        "/api/v1/ai-generation/api/sessions",
        json={"project_id": project_id, "interface_id": interface_id},
        headers=headers,
    )
    assert api_session_resp.status_code == 200, api_session_resp.text
    api_session_id = api_session_resp.json()["data"]["id"]

    api_sse = client.post(
        f"/api/v1/ai-generation/api/sessions/{api_session_id}/messages",
        json={"content": "生成基础用例"},
        headers=headers,
    )
    api_chunks = _consume_sse(api_sse)
    assert any("event: done" in c for c in api_chunks), api_chunks
    print("api session + SSE ok", api_session_id)

    api_session = client.get(
        f"/api/v1/ai-generation/api/sessions/{api_session_id}",
        headers=headers,
    )
    assert api_session.status_code == 200, api_session.text
    base_cases = api_session.json()["data"]["output_payload"].get("base_cases") or []
    assert base_cases, "mock 预览应返回基础用例"

    envs = client.get(
        f"/api/v1/env/environments?project_id={project_id}",
        headers=headers,
    )
    if envs.status_code == 200 and envs.json()["data"]["items"]:
        environment_id = envs.json()["data"]["items"][0]["id"]
        confirm = client.post(
            "/api/v1/ai-generation/api/confirm",
            headers=headers,
            json={
                "session_id": api_session_id,
                "selected_indexes": [0],
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
