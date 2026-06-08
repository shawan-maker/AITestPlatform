"""
端到端测试脚本 - 调试三个问题：
1. 用例详情中测试点显示为 [object Object]
2. 阶段等待无用户提示
3. 会话标题未智能生成
"""

import asyncio
import httpx
import json
import os
from typing import Optional

# 配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# 测试用户凭证（使用正确的账户）
TEST_USERS = [
    {"username": "test1213", "password": "123456"},
]

class E2ETestDebug:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
        self.user_id = None
        self.project_id = None
        self.case_id = None
        
    async def setup(self):
        """登录并获取测试数据"""
        print("\n=== 设置测试环境 ===")
        
        # 1. 尝试多个账户登录
        login_success = False
        for test_user in TEST_USERS:
            print(f"[DEBUG] 尝试登录用户: {test_user['username']}")
            
            # 尝试JSON格式
            login_resp = await self.client.post(
                f"{API_BASE}/auth/login",
                json=test_user
            )
            
            # 如果JSON格式失败，尝试表单格式
            if login_resp.status_code == 422:
                print("[DEBUG] JSON格式失败，尝试表单格式...")
                login_resp = await self.client.post(
                    f"{API_BASE}/auth/login",
                    data=test_user  # 表单数据
                )
            
            if login_resp.status_code == 200:
                print(f"[SUCCESS] 登录成功! 用户: {test_user['username']}")
                login_success = True
                break
            else:
                print(f"[DEBUG] 登录失败: {login_resp.status_code} - {login_resp.text[:100]}")
        
        if not login_success:
            print("[ERROR] 所有账户登录失败")
            return False
        if login_resp.status_code != 200:
            print(f"[ERROR] 登录失败: {login_resp.text}")
            return False
            
        data = login_resp.json()
        self.token = data.get("data", {}).get("access_token")
        if not self.token:
            print(f"[ERROR] 获取token失败: {data}")
            return False
            
        self.client.headers["Authorization"] = f"Bearer {self.token}"
        print(f"[DEBUG] 登录成功, token: {self.token[:20]}...")
        
        # 2. 获取当前用户
        me_resp = await self.client.get(f"{API_BASE}/users/me")
        if me_resp.status_code == 200:
            me_data = me_resp.json().get("data", {})
            self.user_id = me_data.get("id")
            print(f"[DEBUG] 当前用户ID: {self.user_id}")
        
        # 3. 获取项目列表
        projects_resp = await self.client.get(f"{API_BASE}/projects")
        if projects_resp.status_code == 200:
            projects_data = projects_resp.json().get("data", {})
            projects = projects_data.get("items", [])
            if projects:
                self.project_id = projects[0].get("id")
                print(f"[DEBUG] 使用项目ID: {self.project_id}")
            else:
                print("[ERROR] 没有可用的项目")
                return False
        
        return True
    
    async def test_case_detail_test_point(self):
        """测试问题1: 用例详情中测试点显示为 [object Object]"""
        print("\n=== 测试问题1: 用例详情测试点显示 ===")
        
        if not self.project_id:
            print("[ERROR] 没有项目ID，跳过测试")
            return
            
        # 1. 获取用例列表
        cases_resp = await self.client.get(
            f"{API_BASE}/functional/cases",
            params={"project_id": self.project_id, "page": 1, "page_size": 10}
        )
        
        if cases_resp.status_code != 200:
            print(f"[ERROR] 获取用例列表失败: {cases_resp.text}")
            return
            
        cases_data = cases_resp.json().get("data", {})
        cases = cases_data.get("items", [])
        
        if not cases:
            print("[INFO] 没有用例，需要先创建一个用例")
            await self.create_test_case()
            if not self.case_id:
                return
            case_id = self.case_id
        else:
            case_id = cases[0].get("id")
            print(f"[DEBUG] 使用用例ID: {case_id}")
        
        # 2. 获取用例详情
        detail_resp = await self.client.get(
            f"{API_BASE}/functional/cases/{case_id}"
        )
        
        print(f"[DEBUG] 获取用例详情响应状态码: {detail_resp.status_code}")
        
        if detail_resp.status_code != 200:
            print(f"[ERROR] 获取用例详情失败: {detail_resp.text}")
            return
        
        detail_data = detail_resp.json()
        print(f"[DEBUG] 用例详情完整响应:")
        print(json.dumps(detail_data, indent=2, ensure_ascii=False))
        
        # 3. 检查test_point字段
        case_detail = detail_data.get("data", {})
        test_point = case_detail.get("test_point")
        
        print(f"\n[DEBUG] test_point字段类型: {type(test_point)}")
        print(f"[DEBUG] test_point字段值: {test_point}")
        
        if test_point is None:
            print("[INFO] test_point为None，用例可能没有关联测试点")
        elif isinstance(test_point, dict):
            print("[ERROR] test_point是对象类型，这会导致前端显示为[object Object]!")
            print(f"[DEBUG] test_point对象内容: {json.dumps(test_point, indent=2, ensure_ascii=False)}")
            print("[FIX] 需要确保后端返回test_point.test_point字段的值（字符串），而不是整个对象")
        elif isinstance(test_point, str):
            print("[SUCCESS] test_point是字符串类型，应该能正常显示")
            print(f"[DEBUG] test_point内容: {test_point}")
        else:
            print(f"[WARN] test_point是未知类型: {type(test_point)}")
    
    async def create_test_case(self):
        """创建一个测试用例用于测试"""
        print("\n[DEBUG] 创建测试用例...")
        
        # 获取目录
        catalogs_resp = await self.client.get(
            f"{API_BASE}/functional/case-catalogs/tree",
            params={"project_id": self.project_id}
        )
        
        if catalogs_resp.status_code != 200:
            print(f"[ERROR] 获取目录失败: {catalogs_resp.text}")
            return
            
        catalogs_data = catalogs_resp.json().get("data", {})
        catalogs = catalogs_data.get("items", []) if isinstance(catalogs_data, dict) else catalogs_data
        
        if not catalogs:
            print("[ERROR] 没有目录，无法创建用例")
            return
        
        catalog_id = catalogs[0].get("id")
        
        # 创建用例
        create_resp = await self.client.post(
            f"{API_BASE}/functional/cases",
            json={
                "project_id": self.project_id,
                "catalog_id": catalog_id,
                "case_name": "E2E测试用例",
                "priority": "P0",
                "type": "functional",
                "preconditions": "测试前置条件",
                "test_steps": "1. 步骤1\n2. 步骤2",
                "expected_result": "预期结果"
            }
        )
        
        if create_resp.status_code == 200:
            create_data = create_resp.json()
            self.case_id = create_data.get("data", {}).get("id")
            print(f"[DEBUG] 创建用例成功, ID: {self.case_id}")
        else:
            print(f"[ERROR] 创建用例失败: {create_resp.text}")
    
    async def test_session_title_generation(self):
        """测试问题3: 会话标题未智能生成"""
        print("\n=== 测试问题3: 会话标题智能生成 ===")
        
        if not self.project_id:
            print("[ERROR] 没有项目ID，跳过测试")
            return
        
        # 1. 创建功能代理会话
        print("[DEBUG] 创建功能代理会话...")
        
        # 获取目录
        catalogs_resp = await self.client.get(
            f"{API_BASE}/functional/case-catalogs/tree",
            params={"project_id": self.project_id}
        )
        
        if catalogs_resp.status_code != 200:
            print(f"[ERROR] 获取目录失败: {catalogs_resp.text}")
            return
            
        catalogs_data = catalogs_resp.json().get("data", {})
        catalogs = catalogs_data.get("items", []) if isinstance(catalogs_data, dict) else catalogs_data
        
        catalog_id = catalogs[0].get("id") if catalogs else None
        
        create_session_resp = await self.client.post(
            f"{API_BASE}/ai-generation/functional/sessions",
            json={
                "project_id": self.project_id,
                "module_id": None,
                "requirement_text": "测试登录功能，包括用户名和密码验证",
                "user_prompt": "生成登录功能的测试用例"
            }
        )
        
        print(f"[DEBUG] 创建会话响应状态码: {create_session_resp.status_code}")
        
        if create_session_resp.status_code != 200:
            print(f"[ERROR] 创建会话失败: {create_session_resp.text}")
            return
        
        session_data = create_session_resp.json()
        print(f"[DEBUG] 创建会话响应:")
        print(json.dumps(session_data, indent=2, ensure_ascii=False))
        
        session_id = session_data.get("data", {}).get("id")
        session_title = session_data.get("data", {}).get("title")
        
        print(f"[DEBUG] 会话ID: {session_id}")
        print(f"[DEBUG] 初始标题: {session_title}")
        
        if session_title == "新对话":
            print("[INFO] 初始标题为'新对话'（默认值），等待AI生成标题...")
        else:
            print("[INFO] 初始标题不是默认值，可能是根据用户消息生成的")
        
        # 2. 等待SSE流完成（简化版：等待5秒）
        print("[DEBUG] 等待5秒，让SSE流处理...")
        await asyncio.sleep(5)
        
        # 3. 检查会话标题是否已更新
        get_session_resp = await self.client.get(
            f"{API_BASE}/ai-generation/functional/sessions/{session_id}"
        )
        
        if get_session_resp.status_code == 200:
            get_session_data = get_session_resp.json()
            updated_title = get_session_data.get("data", {}).get("title")
            
            print(f"\n[DEBUG] 更新后的标题: {updated_title}")
            
            if updated_title != session_title:
                print("[SUCCESS] 标题已更新!")
                print(f"[DEBUG] 旧标题: {session_title}")
                print(f"[DEBUG] 新标题: {updated_title}")
            else:
                print("[ERROR] 标题未更新!")
                print("[DEBUG] 可能的原因:")
                print("  1. SSE流未完成")
                print("  2. summarize_and_update_title未被调用")
                print("  3. LLM调用失败")
                print("  4. 标题生成逻辑有问题")
        else:
            print(f"[ERROR] 获取会话失败: {get_session_resp.text}")
    
    async def test_stage_waiting_prompt(self):
        """测试问题2: 阶段等待无用户提示"""
        print("\n=== 测试问题2: 阶段等待提示 ===")
        print("[INFO] 这个问题需要前端配合测试，检查浏览器控制台日志")
        print("[INFO] 预期的日志:")
        print("  - '[DEBUG] 检索需求文档阶段完成，等待生成测试用例...'")
        print("  - stage.logs中应包含'检索需求文档阶段完成，正在准备生成测试用例，请稍候...'")
        print("\n[ACTION] 请手动测试:")
        print("  1. 打开前端页面 http://localhost:5173")
        print("  2. 进入功能代理页面")
        print("  3. 输入需求文档，开始生成测试用例")
        print("  4. 观察'检索需求文档'阶段完成后是否有等待提示")
        print("  5. 打开浏览器开发者工具，查看Console日志")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("端到端测试开始")
        print("="*60)
        
        # 设置
        if not await self.setup():
            print("[ERROR] 测试环境设置失败，退出")
            return
        
        # 测试问题1
        await self.test_case_detail_test_point()
        
        # 测试问题3
        await self.test_session_title_generation()
        
        # 测试问题2
        await self.test_stage_waiting_prompt()
        
        print("\n" + "="*60)
        print("端到端测试完成")
        print("="*60)
    
    async def cleanup(self):
        """清理测试数据"""
        await self.client.aclose()

async def main():
    test = E2ETestDebug()
    try:
        await test.run_all_tests()
    finally:
        await test.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
