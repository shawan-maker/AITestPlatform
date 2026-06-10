#!/usr/bin/env python3
"""测试后端 API"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """测试登录"""
    url = f"{BASE_URL}/api/v1/auth/login"
    payload = {
        "username": "test1213",
        "password": "123456"
    }
    
    try:
        # OAuth2 表单登录，使用 data= 而不是 json=
        response = requests.post(url, data=payload)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("[OK] 登录成功")
                return data.get("data", {}).get("access_token")
            else:
                print(f"[FAIL] 登录失败: {data.get('message')}")
                return None
        else:
            print(f"[FAIL] 请求失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] 请求异常: {e}")
        return None

def test_list_projects(token):
    """测试获取项目列表"""
    url = f"{BASE_URL}/api/v1/projects"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("[OK] 获取项目列表成功")
                items = data.get("data", {}).get("items", [])
                if items:
                    print(f"第一个项目 ID: {items[0].get('id')}")
                    return items[0].get('id')
                return None
            else:
                print(f"[FAIL] 获取项目列表失败: {data.get('message')}")
                return None
        else:
            print(f"[FAIL] 请求失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] 请求异常: {e}")
        return None

def test_list_cases(token, project_id):
    """测试获取用例列表"""
    url = f"{BASE_URL}/api/v1/functional/cases"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "project_id": project_id,
        "page": 1,
        "page_size": 10
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"\n状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("[OK] 获取用例列表成功")
                items = data.get("data", {}).get("items", [])
                print(f"用例数量: {len(items)}")
                if items:
                    print(f"第一个用例: {json.dumps(items[0], ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"[FAIL] 获取用例列表失败: {data.get('message')}")
                return False
        else:
            print(f"[FAIL] 请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] 请求异常: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("测试后端 API")
    print("=" * 50)
    
    # 测试登录
    token = test_login()
    
    if token:
        # 测试获取项目列表
        project_id = test_list_projects(token)
        
        if project_id:
            # 测试获取用例列表
            test_list_cases(token, project_id)
        else:
            print("\n[WARN] 未获取到项目 ID，跳过用例列表测试")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
