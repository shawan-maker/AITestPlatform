#!/usr/bin/env python3
"""
测试手工用例管理 API
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_login():
    """登录获取 token"""
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": "test1213",
        "password": "123456",
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        result = response.json()
        print(f"[PASS] 登录成功: {result.get('data', {}).get('username')}")
        return result.get("data", {}).get("access_token")
    else:
        print(f"[FAIL] 登录失败: {response.status_code} - {response.text}")
        return None

def test_get_projects(token):
    """获取用户项目列表"""
    url = f"{BASE_URL}/projects"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        projects = result.get("data", {}).get("items", [])
        print(f"[PASS] 获取项目列表成功: {len(projects)} 个项目")
        return projects
    else:
        print(f"[FAIL] 获取项目列表失败: {response.status_code} - {response.text}")
        return []

def test_list_cases(token, project_id=1):
    """测试获取用例列表"""
    url = f"{BASE_URL}/functional/cases"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "project_id": project_id,
        "page": 1,
        "page_size": 10,
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        result = response.json()
        print(f"[PASS] 获取用例列表成功: {result.get('data', {}).get('total')} 条用例")
        return result.get("data", {}).get("items", [])
    else:
        print(f"[FAIL] 获取用例列表失败: {response.status_code} - {response.text}")
        return []

def test_execute_case(token, case_id):
    """测试执行用例"""
    url = f"{BASE_URL}/functional/cases/{case_id}/execute"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = {
        "exec_result": "passed",
        "jira_issue_key": "TEST-123",
        "remark": "测试执行备注",
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"[PASS] 执行用例成功: case_id={case_id}")
        return True
    else:
        print(f"[FAIL] 执行用例失败: {response.status_code} - {response.text}")
        return False

def main():
    print("=" * 50)
    print("测试手工用例管理 API")
    print("=" * 50)
    
    # 1. 登录
    print("\n1. 测试登录...")
    token = test_login()
    if not token:
        print("登录失败，终止测试")
        return
    
    # 2. 获取用户的项目
    print("\n2. 获取用户项目...")
    projects = test_get_projects(token)
    
    if not projects:
        print("没有可用项目，终止测试")
        return
    
    project_id = projects[0]["id"]
    print(f"使用项目 ID: {project_id}")
    
    # 3. 获取用例列表
    print(f"\n3. 测试获取用例列表 (project_id={project_id})...")
    cases = test_list_cases(token, project_id)
    
    if not cases:
        print("没有用例，跳过执行测试")
        return
    
    # 4. 测试执行用例
    case_id = cases[0].get("id")
    print(f"\n4. 测试执行用例 (case_id={case_id})...")
    test_execute_case(token, case_id)
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    main()
