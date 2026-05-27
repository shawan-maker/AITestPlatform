"""测试执行模块 HTTP 联调脚本。用法: python scripts/test_execution_smoke_test.py"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _login(client: TestClient, username: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_min_env(client: TestClient, headers: dict, project_id: int) -> int:
    cat_resp = client.post(
        f"/api/v1/env/catalogs?project_id={project_id}",
        json={"name": "exec-smoke-catalog"},
        headers=headers,
    )
    assert cat_resp.status_code == 200, cat_resp.text
    catalog_id = cat_resp.json()["data"]["id"]

    env_resp = client.post(
        f"/api/v1/env/environments?project_id={project_id}",
        json={"env_name": "exec_smoke_env", "catalog_id": catalog_id},
        headers=headers,
    )
    assert env_resp.status_code == 200, env_resp.text
    environment_id = env_resp.json()["data"]["id"]

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
    return environment_id


def _poll_suite_progress(
    client: TestClient,
    headers: dict,
    run_id: int,
    *,
    timeout_sec: float = 30.0,
) -> dict:
    deadline = time.time() + timeout_sec
    last = {}
    while time.time() < deadline:
        resp = client.get(
            f"/api/v1/test-execution/runs/suite-runs/{run_id}/progress",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        last = resp.json()["data"]
        if last.get("status") in _TERMINAL_STATUSES:
            return last
        time.sleep(0.3)
    return last


def _run(client: TestClient) -> None:
    token = _login(client, "admin", "123456")
    headers = _auth_headers(token)

    project_name = f"ExecSmoke_{int(time.time())}"
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": project_name, "description": "test execution smoke"},
        headers=headers,
    )
    assert proj_resp.status_code == 200, proj_resp.text
    project_id = proj_resp.json()["data"]["id"]
    print("project ok", project_id)

    environment_id = _create_min_env(client, headers, project_id)
    print("environment ok", environment_id)

    suite_resp = client.post(
        "/api/v1/test-management/suites",
        json={
            "project_id": project_id,
            "suite_name": "exec_smoke_suite",
            "type": "api",
            "environment_id": environment_id,
            "run_mode": "serial",
        },
        headers=headers,
    )
    assert suite_resp.status_code == 200, suite_resp.text
    suite_id = suite_resp.json()["data"]["id"]
    print("suite ok", suite_id)

    trigger = client.post(
        f"/api/v1/test-execution/runs/suites/{suite_id}",
        headers=headers,
    )
    assert trigger.status_code == 200, trigger.text
    run_id = trigger.json()["data"]["suite_run_id"]
    print("trigger ok", run_id)

    progress = _poll_suite_progress(client, headers, run_id)
    print("progress", progress.get("status"), progress.get("percent"))
    assert progress.get("status") in _TERMINAL_STATUSES, progress

    history = client.get(
        f"/api/v1/test-execution/runs/suites/{suite_id}/history",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    assert history.json()["data"]["total"] >= 1

    report = client.get(
        f"/api/v1/test-execution/runs/suite-runs/{run_id}/report",
        headers=headers,
    )
    assert report.status_code == 200, report.text

    client.delete(f"/api/v1/test-management/suites/{suite_id}", headers=headers)
    print("test_execution_smoke_test: OK")


if __name__ == "__main__":
    with TestClient(app) as client:
        _run(client)
