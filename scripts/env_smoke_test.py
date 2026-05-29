"""环境管理模块联调脚本。用法: python scripts/env_smoke_test.py"""

import io
import json
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
    token = _login(client, "admin", "123456")
    headers = _auth_headers(token)

    project_name = f"EnvSmoke_{int(time.time())}"
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": project_name, "description": "env smoke"},
        headers=headers,
    )
    assert proj_resp.status_code == 200, proj_resp.text
    project_id = proj_resp.json()["data"]["id"]
    print("project ok", project_id)

    global_resp = client.put(
        f"/api/v1/env/projects/{project_id}/global-configs",
        json={
            "items": [
                {"name": "global_token", "config_type": "scalar", "value": "g1"},
            ]
        },
        headers=headers,
    )
    assert global_resp.status_code == 200, global_resp.text
    print("global config ok")

    cat_resp = client.post(
        f"/api/v1/env/catalogs?project_id={project_id}",
        json={"name": "默认目录"},
        headers=headers,
    )
    assert cat_resp.status_code == 200, cat_resp.text
    catalog_id = cat_resp.json()["data"]["id"]
    print("catalog ok", catalog_id)

    env_resp = client.post(
        f"/api/v1/env/environments?project_id={project_id}",
        json={"env_name": "dev_env", "catalog_id": catalog_id},
        headers=headers,
    )
    assert env_resp.status_code == 200, env_resp.text
    environment_id = env_resp.json()["data"]["id"]
    print("environment ok", environment_id)

    cfg_resp = client.put(
        f"/api/v1/env/environments/{environment_id}/configs/base",
        json={
            "items": [
                {
                    "name": "base_url",
                    "config_type": "scalar",
                    "value": "http://127.0.0.1:8080",
                }
            ]
        },
        headers=headers,
    )
    assert cfg_resp.status_code == 200, cfg_resp.text

    envs_resp = client.put(
        f"/api/v1/env/environments/{environment_id}/configs/envs",
        json={
            "items": [
                {
                    "name": "global_token",
                    "config_type": "scalar",
                    "value": "env_override",
                }
            ]
        },
        headers=headers,
    )
    assert envs_resp.status_code == 200, envs_resp.text
    print("config ok")

    db_resp = client.post(
        "/api/v1/env/db-connections",
        json={
            "connection_name": f"mysql_{int(time.time())}",
            "server_name": "main_db",
            "db_type": "mysql",
            "config": {
                "host": "127.0.0.1",
                "port": 3306,
                "username": "root",
                "password": "123456",
                "database_name": "test",
            },
            "environment_ids": [environment_id],
        },
        headers=headers,
    )
    assert db_resp.status_code == 200, db_resp.text
    print("db connection ok")

    snap_resp = client.post(
        f"/api/v1/env/environments/{environment_id}/snapshots",
        json={"set_active": True},
        headers=headers,
    )
    assert snap_resp.status_code == 403, snap_resp.text
    print("manual snapshot disabled ok")

    func_name = f"utils_{int(time.time())}.py"
    func_resp = client.post(
        "/api/v1/env/function-files",
        json={
            "file_name": func_name,
            "source_code": "def hello():\n    return 1\n",
            "environment_ids": [environment_id],
        },
        headers=headers,
    )
    assert func_resp.status_code == 200, func_resp.text
    print("function file ok")

    validate_resp = client.post(
        "/api/v1/env/function-files/validate",
        json={"file_name": func_name, "source_code": "def hello():\n    return 1\n"},
        headers=headers,
    )
    assert validate_resp.status_code == 200, validate_resp.text
    assert validate_resp.json()["data"]["valid"] is True
    print("function validate ok")

    upload_resp = client.post(
        f"/api/v1/env/uploaded-files?project_id={project_id}",
        files={"file": ("smoke.txt", b"smoke content", "text/plain")},
        headers=headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    uploaded_file_id = upload_resp.json()["data"]["id"]
    print("upload ok", uploaded_file_id)

    resolve_resp = client.get(
        f"/api/v1/env/uploaded-files/{uploaded_file_id}/resolve-path",
        headers=headers,
    )
    assert resolve_resp.status_code == 200, resolve_resp.text
    resolve_data = resolve_resp.json()["data"]
    assert resolve_data["file_name"] == "smoke.txt"
    assert resolve_data["storage_key"]
    assert Path(resolve_data["absolute_path"]).is_file()
    print("resolve-path ok", resolve_data["absolute_path"])

    export_resp = client.get(
        f"/api/v1/env/environments/{environment_id}/export",
        headers=headers,
    )
    assert export_resp.status_code == 200, export_resp.text
    bundle = export_resp.json()["data"]
    assert bundle.get("functions"), "export should include embedded functions"
    assert bundle.get("db_connections"), "export should include embedded db_connections"
    assert bundle.get("import_mode") == "embed"
    print("export ok")

    import_name = f"imported_{int(time.time())}"
    import_bundle = {**bundle, "env_name": import_name}
    import_resp = client.post(
        f"/api/v1/env/environments/import?project_id={project_id}",
        json={"bundle": import_bundle, "overwrite": False, "import_mode": "embed"},
        headers=headers,
    )
    assert import_resp.status_code == 200, import_resp.text
    imported_env_id = import_resp.json()["data"]["environment_id"]
    print("import embed ok", imported_env_id)

    bundle_bytes = json.dumps(import_bundle, ensure_ascii=False).encode("utf-8")
    import_file_resp = client.post(
        f"/api/v1/env/environments/import-file?project_id={project_id}&overwrite=false&import_mode=embed",
        files={"file": ("bundle.json", io.BytesIO(bundle_bytes), "application/json")},
        headers=headers,
    )
    assert import_file_resp.status_code == 409, import_file_resp.text
    import_bundle["env_name"] = f"file_import_{int(time.time())}"
    bundle_bytes = json.dumps(import_bundle, ensure_ascii=False).encode("utf-8")
    import_file_resp = client.post(
        f"/api/v1/env/environments/import-file?project_id={project_id}&overwrite=false&import_mode=embed",
        files={"file": ("bundle.json", io.BytesIO(bundle_bytes), "application/json")},
        headers=headers,
    )
    assert import_file_resp.status_code == 200, import_file_resp.text
    print("import-file embed ok")

    test_data_resp = client.get(
        f"/api/v1/env/environments/{environment_id}/test-env-data",
        headers=headers,
    )
    assert test_data_resp.status_code == 200, test_data_resp.text
    assert test_data_resp.json()["data"]["base_url"]
    envs = test_data_resp.json()["data"].get("envs") or {}
    assert envs.get("global_token") == "env_override", "env should override global on merge"
    print("test-env-data ok")

    client.delete(f"/api/v1/env/environments/{environment_id}", headers=headers)
    client.delete(f"/api/v1/env/environments/{imported_env_id}", headers=headers)
    client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    print("ALL PASSED")


def main() -> None:
    with TestClient(app) as client:
        _run(client)


if __name__ == "__main__":
    main()
