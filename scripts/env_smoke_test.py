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
    db_id = db_resp.json()["data"]["id"]
    print("db connection ok")

    db_unbound_resp = client.post(
        f"/api/v1/env/db-connections?project_id={project_id}",
        json={
            "connection_name": f"unbound_{int(time.time())}",
            "server_name": "unbound_db",
            "db_type": "mysql",
            "config": {
                "host": "127.0.0.1",
                "port": 3306,
                "username": "root",
                "password": "123456",
                "database_name": "test",
            },
            "environment_ids": [],
        },
        headers=headers,
    )
    assert db_unbound_resp.status_code == 200, db_unbound_resp.text
    unbound_db_id = db_unbound_resp.json()["data"]["id"]

    db_update_resp = client.patch(
        f"/api/v1/env/db-connections/{unbound_db_id}?project_id={project_id}",
        json={
            "connection_name": f"unbound_updated_{int(time.time())}",
            "environment_ids": [],
        },
        headers=headers,
    )
    assert db_update_resp.status_code == 200, db_update_resp.text

    db_list_resp = client.get(
        f"/api/v1/env/db-connections?project_id={project_id}&page=1&page_size=100",
        headers=headers,
    )
    assert db_list_resp.status_code == 200, db_list_resp.text
    listed_ids = {item["id"] for item in db_list_resp.json()["data"]["items"]}
    assert unbound_db_id in listed_ids, "updated unbound db connection should remain in project list"
    print("db connection update list ok")

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
            "source_code": (
                "def hello():\n    return 1\n\n"
                "def get_delta_time():\n    return 2\n"
            ),
            "environment_ids": [environment_id],
        },
        headers=headers,
    )
    assert func_resp.status_code == 200, func_resp.text
    func_id = func_resp.json()["data"]["id"]
    print("function file ok", func_id)

    debug_ok = client.post(
        f"/api/v1/env/function-files/{func_id}/debug",
        json={"method_name": "hello", "params": {}},
        headers=headers,
    )
    assert debug_ok.status_code == 200, debug_ok.text
    assert debug_ok.json()["data"]["success"] is True
    print("function debug ok")

    func_import_name = f"mathfn_{int(time.time())}.py"
    func_import_resp = client.post(
        "/api/v1/env/function-files",
        json={
            "file_name": func_import_name,
            "source_code": (
                "import math\n"
                "def add(num1, num2):\n"
                "    return num1 + num2 + int(math.sqrt(4))\n"
            ),
            "environment_ids": [environment_id],
        },
        headers=headers,
    )
    assert func_import_resp.status_code == 200, func_import_resp.text
    func_import_id = func_import_resp.json()["data"]["id"]
    debug_import = client.post(
        f"/api/v1/env/function-files/{func_import_id}/debug",
        json={"method_name": "add", "params": {"num1": 1, "num2": 2}},
        headers=headers,
    )
    assert debug_import.status_code == 200, debug_import.text
    assert debug_import.json()["data"]["success"] is True
    assert debug_import.json()["data"]["result"] == 5
    print("function debug with import ok")

    func_main_name = f"mainfn_{int(time.time())}.py"
    func_main_resp = client.post(
        "/api/v1/env/function-files",
        json={
            "file_name": func_main_name,
            "source_code": (
                "def add(num1, num2):\n"
                "    return num1 + num2\n"
                "if __name__ == '__main__':\n"
                "    pass\n"
            ),
            "environment_ids": [environment_id],
        },
        headers=headers,
    )
    assert func_main_resp.status_code == 200, func_main_resp.text
    func_main_id = func_main_resp.json()["data"]["id"]
    debug_main = client.post(
        f"/api/v1/env/function-files/{func_main_id}/debug",
        json={"method_name": "add", "params": {"num1": "1", "num2": "2"}},
        headers=headers,
    )
    assert debug_main.status_code == 200, debug_main.text
    assert debug_main.json()["data"]["success"] is True
    assert debug_main.json()["data"]["result"] == 3
    assert "print_out" in debug_main.json()["data"]
    assert "error" in debug_main.json()["data"]
    print("function debug with __name__ ok")

    func_print_name = f"printfn_{int(time.time())}.py"
    func_print_resp = client.post(
        "/api/v1/env/function-files",
        json={
            "file_name": func_print_name,
            "source_code": (
                "def greet(name):\n"
                "    print(f'hello {name}')\n"
                "    return name\n"
            ),
            "environment_ids": [environment_id],
        },
        headers=headers,
    )
    assert func_print_resp.status_code == 200, func_print_resp.text
    func_print_id = func_print_resp.json()["data"]["id"]
    debug_print = client.post(
        f"/api/v1/env/function-files/{func_print_id}/debug",
        json={"method_name": "greet", "params": {"name": "world"}},
        headers=headers,
    )
    assert debug_print.status_code == 200, debug_print.text
    body = debug_print.json()["data"]
    assert body["success"] is True
    assert body["result"] == "world"
    assert "hello world" in body["print_out"]
    print("function debug print_out ok")

    func_with_var = f"echo_{int(time.time())}.py"
    func_var_resp = client.post(
        "/api/v1/env/function-files",
        json={
            "file_name": func_with_var,
            "source_code": "def echo(v):\n    return v\n",
            "environment_ids": [environment_id],
        },
        headers=headers,
    )
    assert func_var_resp.status_code == 200, func_var_resp.text
    func_var_id = func_var_resp.json()["data"]["id"]

    debug_var = client.post(
        f"/api/v1/env/function-files/{func_var_id}/debug",
        json={
            "method_name": "echo",
            "params": {"v": "$global_token"},
            "environment_id": environment_id,
        },
        headers=headers,
    )
    assert debug_var.status_code == 200, debug_var.text
    assert debug_var.json()["data"]["success"] is True
    assert debug_var.json()["data"]["result"] == "env_override"
    print("function debug with env ok")

    debug_missing_env = client.post(
        f"/api/v1/env/function-files/{func_var_id}/debug",
        json={"method_name": "echo", "params": {"v": "$global_token"}},
        headers=headers,
    )
    assert debug_missing_env.status_code == 400, debug_missing_env.text
    print("function debug env required ok")

    list_fn = client.get(
        f"/api/v1/env/function-files?project_id={project_id}&keyword={func_name[:8]}",
        headers=headers,
    )
    assert list_fn.status_code == 200, list_fn.text
    assert list_fn.json()["data"]["total"] >= 1
    item = list_fn.json()["data"]["items"][0]
    assert "method_names" in item
    assert "environment_names" in item
    assert "hello" in item["method_names"]
    print("function keyword filter ok")

    list_method = client.get(
        f"/api/v1/env/function-files?project_id={project_id}&method_name=hello",
        headers=headers,
    )
    assert list_method.status_code == 200, list_method.text
    assert list_method.json()["data"]["total"] >= 1
    print("function method filter ok")

    list_method_partial = client.get(
        f"/api/v1/env/function-files?project_id={project_id}&method_name=time",
        headers=headers,
    )
    assert list_method_partial.status_code == 200, list_method_partial.text
    assert list_method_partial.json()["data"]["total"] >= 1
    print("function method partial filter ok")

    bound_envs = client.get(
        f"/api/v1/env/function-files/bound-environments?project_id={project_id}",
        headers=headers,
    )
    assert bound_envs.status_code == 200, bound_envs.text
    assert len(bound_envs.json()["data"]) >= 1
    print("function bound environments ok")

    list_env = client.get(
        f"/api/v1/env/function-files?project_id={project_id}&environment_id={environment_id}",
        headers=headers,
    )
    assert list_env.status_code == 200, list_env.text
    assert list_env.json()["data"]["total"] >= 1
    print("function environment filter ok")

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

    list_files = client.get(
        f"/api/v1/env/uploaded-files?project_id={project_id}&keyword=smoke",
        headers=headers,
    )
    assert list_files.status_code == 200, list_files.text
    assert list_files.json()["data"]["total"] >= 1
    print("file keyword filter ok")

    list_txt = client.get(
        f"/api/v1/env/uploaded-files?project_id={project_id}&mime_type=txt",
        headers=headers,
    )
    assert list_txt.status_code == 200, list_txt.text
    assert list_txt.json()["data"]["total"] >= 1
    print("file txt extension filter ok")

    download_resp = client.get(
        f"/api/v1/env/uploaded-files/{uploaded_file_id}/download",
        headers=headers,
    )
    assert download_resp.status_code == 200, download_resp.text
    assert b"smoke content" in download_resp.content
    print("file download ok")

    upload_json = client.post(
        f"/api/v1/env/uploaded-files?project_id={project_id}",
        files={"file": ("data.json", b'{"hello": "world"}', "application/json")},
        headers=headers,
    )
    assert upload_json.status_code == 200, upload_json.text
    json_file_id = upload_json.json()["data"]["id"]
    download_json = client.get(
        f"/api/v1/env/uploaded-files/{json_file_id}/download",
        headers=headers,
    )
    assert download_json.status_code == 200, download_json.text
    assert b'"hello"' in download_json.content
    print("file json download ok")

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
