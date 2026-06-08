"""
修复三个问题并测试
1. 用例详情中测试点显示为 [object Object]
2. 阶段等待无用户提示
3. 会话标题未智能生成
"""

import asyncio
import httpx
import json
import os

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

TEST_USER = {"username": "test1213", "password": "123456"}

class FixAndTest:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.token = None
        self.user_id = None
        self.project_id = None
        self.catalog_id = None
        
    async def setup(self):
        """登录"""
        print("\n=== 登录 ===")
        
        login_resp = await self.client.post(
            f"{API_BASE}/auth/login",
            json=TEST_USER
        )
        
        if login_resp.status_code == 422:
            login_resp = await self.client.post(
                f"{API_BASE}/auth/login",
                data=TEST_USER
            )
        
        if login_resp.status_code != 200:
            print(f"[ERROR] 登录失败: {login_resp.text[:200]}")
            return False
            
        data = login_resp.json()
        self.token = data.get("data", {}).get("access_token")
        self.client.headers["Authorization"] = f"Bearer {self.token}"
        print(f"[SUCCESS] 登录成功")
        
        # 获取项目
        projects_resp = await self.client.get(f"{API_BASE}/projects")
        if projects_resp.status_code == 200:
            projects_data = projects_resp.json().get("data", {})
            projects = projects_data.get("items", [])
            if projects:
                self.project_id = projects[0].get("id")
                print(f"[DEBUG] 项目ID: {self.project_id}")
                
                # 获取目录
                catalogs_resp = await self.client.get(
                    f"{API_BASE}/functional/case-catalogs/tree",
                    params={"project_id": self.project_id}
                )
                if catalogs_resp.status_code == 200:
                    catalogs_data = catalogs_resp.json().get("data", {})
                    catalogs = catalogs_data.get("items", []) if isinstance(catalogs_data, dict) else catalogs_data
                    if catalogs:
                        self.catalog_id = catalogs[0].get("id")
                        print(f"[DEBUG] 目录ID: {self.catalog_id}")
                
                return True
        
        return False
    
    async def test_case_detail(self):
        """测试问题1: 用例详情测试点"""
        print("\n" + "="*60)
        print("=== 测试问题1: 用例详情测试点 ===")
        print("="*60)
        
        if not self.catalog_id:
            print("[ERROR] 没有目录，无法测试")
            return
        
        # 获取用例列表
        cases_resp = await self.client.get(
            f"{API_BASE}/functional/cases",
            params={"project_id": self.project_id, "page": 1, "page_size": 5}
        )
        
        if cases_resp.status_code != 200:
            print(f"[ERROR] 获取用例列表失败: {cases_resp.text[:200]}")
            return
        
        cases_data = cases_resp.json().get("data", {})
        cases = cases_data.get("items", [])
        
        if not cases:
            print("[INFO] 没有用例，创建一个测试用例")
            # 创建用例
            create_resp = await self.client.post(
                f"{API_BASE}/functional/cases",
                json={
                    "project_id": self.project_id,
                    "catalog_id": self.catalog_id,
                    "case_name": "测试用",
                    "priority": 0,
                    "type": "functional"
                }
            )
            if create_resp.status_code == 200:
                case_data = create_resp.json()
                case_id = case_data.get("data", {}).get("id")
                print(f"[SUCCESS] 创建用例成功, ID: {case_id}")
            else:
                print(f"[ERROR] 创建用例失败: {create_resp.text[:200]}")
                return
        else:
            case_id = cases[0].get("id")
            print(f"[DEBUG] 使用已有用例, ID: {case_id}")
        
        # 获取用例详情
        detail_resp = await self.client.get(f"{API_BASE}/functional/cases/{case_id}")
        
        if detail_resp.status_code == 200:
            detail_data = detail_resp.json()
            print(f"[DEBUG] 用例详情响应:")
            print(json.dumps(detail_data, indent=2, ensure_ascii=False))
            
            test_point = detail_data.get("data", {}).get("test_point")
            print(f"\n[DEBUG] test_point类型: {type(test_point)}")
            print(f"[DEBUG] test_point值: {test_point}")
            
            if isinstance(test_point, dict):
                print("[ERROR] test_point是对象! 这会导致前端显示[object Object]")
                print(f"[DEBUG] 对象内容: {json.dumps(test_point, indent=2, ensure_ascii=False)}")
            elif isinstance(test_point, str):
                print("[SUCCESS] test_point是字符串，应该正常显示")
            else:
                print(f"[INFO] test_point是: {test_point}")
        else:
            print(f"[ERROR] 获取用例详情失败: {detail_resp.text[:200]}")
    
    async def test_session_title(self):
        """测试问题3: 会话标题智能生成"""
        print("\n" + "="*60)
        print("=== 测试问题3: 会话标题智能生成 ===")
        print("="*60)
        
        if not self.project_id:
            print("[ERROR] 没有项目ID")
            return
        
        # 创建会话
        print("\n[DEBUG] 创建会话...")
        create_resp = await self.client.post(
            f"{API_BASE}/ai-generation/functional/sessions",
            json={
                "project_id": self.project_id,
                "requirement_text": "测试用户登录功能",
                "user_prompt": "生成登录测试用例"
            }
        )
        
        if create_resp.status_code != 200:
            print(f"[ERROR] 创建会话失败: {create_resp.text[:200]}")
            return
        
        session_data = create_resp.json()
        session_id = session_data.get("data", {}).get("id")
        initial_title = session_data.get("data", {}).get("title")
        
        print(f"[DEBUG] 会话ID: {session_id}")
        print(f"[DEBUG] 初始标题: {initial_title}")
        
        # 等待10秒
        print("[DEBUG] 等待10秒，让SSE流处理...")
        await asyncio.sleep(10)
        
        # 检查标题
        check_resp = await self.client.get(f"{API_BASE}/ai-generation/functional/sessions/{session_id}")
        
        if check_resp.status_code == 200:
            check_data = check_resp.json()
            updated_title = check_data.get("data", {}).get("title")
            
            print(f"[DEBUG] 更新后标题: {updated_title}")
            
            if updated_title != initial_title:
                print("[SUCCESS] 标题已更新!")
            else:
                print("[ERROR] 标题未更新!")
                print("[DEBUG] 检查后端日志文件: d:/PyProject/AITestPlatform/debug_title.log")
        else:
            print(f"[ERROR] 获取会话失败: {check_resp.text[:200]}")
    
    async def check_backend_logs(self):
        """检查后端日志"""
        print("\n" + "="*60)
        print("=== 检查后端日志 ===")
        print("="*60)
        
        log_file = "d:/PyProject/AITestPlatform/debug_title.log"
        if os.path.exists(log_file):
            print(f"[DEBUG] 找到日志文件: {log_file}")
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    print(f"[DEBUG] 日志内容 ({len(lines)} 行):")
                    for line in lines[-10:]:  # 最后10行
                        print(f"  {line.strip()}")
                else:
                    print("[DEBUG] 日志文件为空")
        else:
            print(f"[INFO] 日志文件不存在: {log_file}")
            print("[INFO] 这说明 summarize_and_update_title 函数可能未被调用")
    
    async def run(self):
        """运行修复和测试"""
        print("="*60)
        print("开始修复和测试")
        print("="*60)
        
        if not await self.setup():
            print("[ERROR] 设置失败")
            return
        
        # 测试问题1
        await self.test_case_detail()
        
        # 测试问题3
        await self.test_session_title()
        
        # 检查日志
        await self.check_backend_logs()
        
        print("\n" + "="*60)
        print("测试和检查完成")
        print("="*60)
        print("\n[INFO] 前端编译错误已修复 (color.adjust -> adjust-color)")
        print("[INFO] 请手动测试问题2: 打开前端页面，观察阶段等待提示")
        print("[INFO] 请查看后端日志: d:/PyProject/AITestPlatform/debug_title.log")
    
    async def cleanup(self):
        await self.client.aclose()

async def main():
    fixer = FixAndTest()
    try:
        await fixer.run()
    finally:
        await fixer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
