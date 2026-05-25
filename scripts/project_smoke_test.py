"""项目管理模块联调脚本。用法: python scripts/project_smoke_test.py"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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


def _run(client: TestClient) -> None:
    admin_token = _login(client, "admin", "123456")
    h_admin = _auth_headers(admin_token)

    project_name = f"SmokeTestProject_{int(time.time())}"
    create_resp = client.post(
        "/api/v1/projects",
        json={"name": project_name, "description": "smoke test"},
        headers=h_admin,
    )
    assert create_resp.status_code == 200, create_resp.text
    project = create_resp.json()["data"]
    project_id = project["id"]
    assert project["my_role"] == 2
    assert project["members"] is not None
    print("create ok", project_id)

    list_resp = client.get("/api/v1/projects", headers=h_admin)
    assert list_resp.status_code == 200
    assert list_resp.json()["data"]["total"] >= 1
    print("list ok")

    detail_resp = client.get(f"/api/v1/projects/{project_id}", headers=h_admin)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["members"] is not None
    print("detail ok")

    patch_resp = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"description": "updated"},
        headers=h_admin,
    )
    assert patch_resp.status_code == 200
    print("patch ok")

    delete_resp = client.delete(f"/api/v1/projects/{project_id}", headers=h_admin)
    assert delete_resp.status_code == 200, delete_resp.text
    print("delete ok")

    print("ALL PASSED")


def main() -> None:
    with TestClient(app) as client:
        _run(client)


if __name__ == "__main__":
    main()
