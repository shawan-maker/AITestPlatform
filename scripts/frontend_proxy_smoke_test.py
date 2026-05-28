"""前端 Vite 代理联调：经 dev server 访问后端 API（模拟浏览器 axios 路径）。

用法:
  python scripts/frontend_proxy_smoke_test.py
  python scripts/frontend_proxy_smoke_test.py --base http://localhost:5174
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
import json


def request(method: str, url: str, headers: dict | None = None, data: dict | None = None, form: bool = False):
    body = None
    hdrs = dict(headers or {})
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            body = json.dumps(data).encode()
            hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return e.code, payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:5174", help="Vite dev server origin")
    args = parser.parse_args()
    api = f"{args.base.rstrip('/')}/api/v1"
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        if ok:
            print(f"OK  {name}" + (f" — {detail}" if detail else ""))
        else:
            print(f"FAIL {name}" + (f" — {detail}" if detail else ""))
            failures.append(name)

    # 1. 前端 SPA 入口
    try:
        with urllib.request.urlopen(f"{args.base}/", timeout=10) as resp:
            html = resp.read(500).decode(errors="ignore")
        check("SPA index", resp.status == 200 and "<!DOCTYPE html" in html.lower() or "html" in html.lower())
    except Exception as e:
        check("SPA index", False, str(e))

    # 2. 登录（OAuth2 form，与前端一致）
    status, login = request("POST", f"{api}/auth/login", form=True, data={"username": "admin", "password": "123456"})
    token = login.get("data", {}).get("access_token") or login.get("access_token")
    check("auth/login", status == 200 and bool(token), f"status={status}")

    if not token:
        print("\nABORT: cannot continue without token")
        sys.exit(1)

    auth = {"Authorization": f"Bearer {token}"}

    # 取一个项目 ID（前端 ProjectContextBar 选定后注入 query）
    st, proj_body = request("GET", f"{api}/projects", headers=auth)
    projects = proj_body.get("data", {}).get("items") or proj_body.get("data") or []
    if isinstance(projects, dict):
        projects = projects.get("items", [])
    project_id = projects[0]["id"] if projects else None
    check("projects has item", bool(project_id), f"project_id={project_id}")

    q = f"?project_id={project_id}" if project_id else ""

    # 3. 核心读接口（F2–F8 前端会调用的子集）
    endpoints = [
        ("GET", f"{api}/users/me", None, "users/me"),
        ("GET", f"{api}/projects", None, "projects"),
        ("GET", f"{api}/knowledge/documents{q}", None, "knowledge/documents"),
        ("GET", f"{api}/functional/requirements{q}", None, "functional/requirements"),
        ("GET", f"{api}/env/catalogs/tree{q}", None, "env/catalogs/tree"),
        ("GET", f"{api}/api-test/catalogs/tree{q}", None, "api-test/catalogs/tree"),
        ("GET", f"{api}/test-management/suites{q}", None, "test-management/suites"),
        ("GET", f"{api}/test-management/tasks{q}", None, "test-management/tasks"),
        ("GET", f"{api}/test-management/defects{q}", None, "test-management/defects"),
        ("GET", f"{api}/ai-generation/meta", None, "ai-generation/meta"),
    ]

    for method, url, _, label in endpoints:
        st, body = request(method, url, headers=auth)
        code = body.get("code")
        ok = st == 200 and (code in (0, 200, None) or "data" in body)
        check(f"proxy {label}", ok, f"http={st} code={code}")

    print()
    if failures:
        print(f"FAILED ({len(failures)}): {', '.join(failures)}")
        sys.exit(1)
    print("ALL FRONTEND PROXY CHECKS PASSED")


if __name__ == "__main__":
    main()
