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

    lookup_resp = client.get("/api/v1/users/lookup", params={"q": "admin"}, headers=h_admin)
    assert lookup_resp.status_code == 200, lookup_resp.text
    lookup_items = lookup_resp.json()["data"]["items"]
    assert len(lookup_items) >= 1
    assert "is_super_admin" not in lookup_items[0]
    print("lookup ok")

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
    items = list_resp.json()["data"]["items"]
    assert list_resp.json()["data"]["total"] >= 1
    listed = next(i for i in items if i["id"] == project_id)
    assert listed.get("member_count", 0) >= 1
    print("list ok member_count=", listed.get("member_count"))

    detail_resp = client.get(f"/api/v1/projects/{project_id}", headers=h_admin)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["members"] is not None
    admin_member = next(m for m in detail["members"] if m["role"] == 2)
    assert admin_member.get("is_super_admin") is True
    print("detail ok is_super_admin on member")

    patch_resp = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"description": "updated"},
        headers=h_admin,
    )
    assert patch_resp.status_code == 200
    print("patch ok")

    # create temp user and add as editor, then SA promotes via PATCH role=2
    suffix = int(time.time())
    user_body = {
        "username": f"smoke_editor_{suffix}",
        "email": f"smoke_editor_{suffix}@test.com",
        "password": "123456",
        "verify_password": "123456",
        "is_super_admin": False,
    }
    user_resp = client.post("/api/v1/users", json=user_body, headers=h_admin)
    assert user_resp.status_code == 200, user_resp.text
    editor_id = user_resp.json()["data"]["id"]

    add_member = client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": editor_id, "role": 1},
        headers=h_admin,
    )
    assert add_member.status_code == 200, add_member.text
    print("add editor ok")

    promote = client.patch(
        f"/api/v1/projects/{project_id}/members/{editor_id}",
        json={"role": 2},
        headers=h_admin,
    )
    assert promote.status_code == 200, promote.text
    assert promote.json()["data"]["role"] == 2
    after = client.get(f"/api/v1/projects/{project_id}", headers=h_admin).json()["data"]
    roles = {m["user_id"]: m["role"] for m in after["members"]}
    admin_user_id = admin_member["user_id"]
    assert roles[editor_id] == 2
    assert roles[admin_user_id] == 1
    print("promote admin via PATCH ok")

    # create second project for batch delete
    project_name2 = f"SmokeTestProject2_{int(time.time())}"
    create2 = client.post(
        "/api/v1/projects",
        json={"name": project_name2, "description": "batch"},
        headers=h_admin,
    )
    assert create2.status_code == 200, create2.text
    project_id2 = create2.json()["data"]["id"]
    print("create2 ok", project_id2)

    batch_resp = client.post(
        "/api/v1/projects/batch-delete",
        json={"project_ids": [project_id, project_id2]},
        headers=h_admin,
    )
    assert batch_resp.status_code == 200, batch_resp.text
    batch_data = batch_resp.json()["data"]
    assert project_id in batch_data["deleted_ids"]
    assert project_id2 in batch_data["deleted_ids"]
    assert not batch_data.get("failures")
    print("batch-delete ok")

    # cleanup temp user
    client.delete(f"/api/v1/users/{editor_id}", headers=h_admin)

    print("ALL PASSED")


def main() -> None:
    with TestClient(app) as client:
        _run(client)


if __name__ == "__main__":
    main()
