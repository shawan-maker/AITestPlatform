"""接口测试模块联调脚本。用法: API_TEST_GEN_MOCK=1 python scripts/api_test_smoke_test.py"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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


def main() -> None:
    with TestClient(app) as client:
        token = _login(client, "admin", "123456")
        headers = _auth_headers(token)

        projects = client.get("/api/v1/projects", headers=headers)
        assert projects.status_code == 200, projects.text
        project_list = projects.json()["data"]["items"]
        assert project_list, "需要至少一个项目"
        project_id = project_list[0]["id"]

        cat_resp = client.post(
            f"/api/v1/api-test/catalogs?project_id={project_id}",
            headers=headers,
            json={"name": "smoke-api-catalog"},
        )
        assert cat_resp.status_code == 200, cat_resp.text
        catalog_id = cat_resp.json()["data"]["id"]

        tree = client.get(
            f"/api/v1/api-test/catalogs/tree?project_id={project_id}",
            headers=headers,
        )
        assert tree.status_code == 200, tree.text

        iface_resp = client.post(
            "/api/v1/api-test/interfaces",
            headers=headers,
            json={
                "project_id": project_id,
                "catalog_id": catalog_id,
                "method": "GET",
                "path": "/smoke/ping",
                "summary": "smoke ping",
                "parameters": {"header": [], "path": [], "query": []},
                "responses": [],
            },
        )
        assert iface_resp.status_code == 200, iface_resp.text
        interface_id = iface_resp.json()["data"]["id"]

        deps = client.get(
            f"/api/v1/api-test/interfaces/{interface_id}/dependencies",
            headers=headers,
        )
        assert deps.status_code == 200, deps.text

        doc = client.get(
            f"/api/v1/api-test/interfaces/{interface_id}/doc-preview",
            headers=headers,
        )
        assert doc.status_code == 200, doc.text

        fill = client.post(
            f"/api/v1/api-test/interfaces/{interface_id}/debug-template/fill-from-doc",
            headers=headers,
        )
        assert fill.status_code == 200, fill.text

        preview = client.post(
            "/api/v1/ai-generation/api/generate-from-interface",
            headers=headers,
            json={"interface_id": interface_id, "user_prompt": "smoke"},
        )
        assert preview.status_code == 200, preview.text
        session_id = preview.json()["data"]["session_id"]
        base_cases = preview.json()["data"]["base_cases"]
        assert base_cases, "mock 预览应返回基础用例"

        envs = client.get(
            f"/api/v1/env/environments?project_id={project_id}",
            headers=headers,
        )
        environment_id = None
        if envs.status_code == 200 and envs.json()["data"]["items"]:
            environment_id = envs.json()["data"]["items"][0]["id"]

        if environment_id:
            selected = list(range(min(2, len(base_cases))))
            confirm = client.post(
                "/api/v1/ai-generation/api/confirm",
                headers=headers,
                json={
                    "session_id": session_id,
                    "selected_indexes": selected,
                    "environment_id": environment_id,
                    "interface_id": interface_id,
                },
            )
            assert confirm.status_code == 200, confirm.text
            confirm_data = confirm.json()["data"]
            case_ids = confirm_data["created_case_ids"]
            base_ids = confirm_data["created_base_case_ids"]
            assert len(case_ids) == len(selected), "并发确认应创建与选中数相同的用例"
            assert len(base_ids) == len(selected), "并发确认应创建与选中数相同的基础用例"

            cases = client.get(
                f"/api/v1/api-test/interfaces/{interface_id}/cases?case_kind=main",
                headers=headers,
            )
            assert cases.status_code == 200, cases.text

        copy_resp = client.post(
            f"/api/v1/api-test/interfaces/{interface_id}/copy",
            headers=headers,
        )
        assert copy_resp.status_code == 200, copy_resp.text

        client.delete(
            f"/api/v1/api-test/interfaces/{interface_id}",
            headers=headers,
        )
        client.delete(
            f"/api/v1/api-test/catalogs/{catalog_id}",
            headers=headers,
        )

    print("api_test_smoke_test: OK")


if __name__ == "__main__":
    main()
