"""Standalone LangGraph agent demo (not platform FastAPI API).

用法: python scripts/demos/agent_demo.py
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.case_generate_agent import AgentManage, RuntimeContext
from agents.memory import DualMemoryManager

agent = AgentManage.create_supervisor_agent()

context = RuntimeContext(
    project_name="tpshop",
    module_id="001",
    user_id="user001",
    session_id="session001",
    thread_id="thread_001",
)


async def main():
    print("=======================第4步：接口文档的检索和生成功能用例=====================================")
    result4 = AgentManage.agent_chat(
        agent, "请给出登录接口的所有请求和响应信息，并生成接口测试用例", context
    )
    async for i in result4:
        if i.get("type") == "custom":
            print(i.get("content"), end="", flush=True)
        elif i.get("type") == "messages":
            print(i.get("content"), end="", flush=True)
    print("\n=============================第5步=========================================================")
    print(f"所有长期记忆：{DualMemoryManager().load_long_term_memories(context)}")


if __name__ == "__main__":
    asyncio.run(main())
