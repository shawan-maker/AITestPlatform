import asyncio

from agents.case_generate_agent import AgentManage, RuntimeContext
from agents.memory import DualMemoryManager

# ============================================================
# 主程序入口 —— 测试双记忆系统完整流程
# ============================================================

# 创建 supervisor agent（内部自动挂载 checkeeper + memory_store）
agent = AgentManage.create_supervisor_agent()

# 创建运行上下文参数
#   user_id + session_id → 定位长期记忆命名空间（跨会话持久化）
#   thread_id           → 定位短期记忆线程（同一会话内的多轮对话）
context = RuntimeContext(
    project_name="tpshop",
    module_id="001",
    user_id="user001",
    session_id="session001",
    thread_id="thread_001"
)

# # ========== 第1轮：功能测试用例生成 ==========
# print("=======================需求文档的检索和生成功能用例=====================================")
# print("=======================第1步=====================================")
# result1 = AgentManage.agent_chat(agent, "请在tpshop项目中检索出登录的功能需求，并编写功能测试用例", context)
# # result1 = AgentManage.agent_chat(agent, "我是石头，请记住我的名字", context)
# for i in result1:
#     if i.get("type") == "custom":
#         print(i.get("content"), end="", flush=True)
#     elif i.get("type") == "messages":
#         print(i.get("content"), end="", flush=True)
#
# # ========== 第2轮：基于上下文继续对话（checkeeper 自动管理多轮） ==========
# print("\n=======================第2步=====================================")
# result2 = AgentManage.agent_chat(agent, "请搜索tpshop项目的功能需求，检查还有哪些功能需求没有编写测试用例", context)
# # result2 = AgentManage.agent_chat(agent, "我的名字是什么？", context)
# for i in result2:
#     if i.get("type") == "custom":
#         print(i.get("content"), end="", flush=True)
#     elif i.get("type") == "messages":
#         print(i.get("content"), end="", flush=True)
#
# # ========== 第3轮：继续深入 ==========
# print("\n=======================第3步=====================================")
# result3 = AgentManage.agent_chat(agent, "在tpshop项目中未覆盖的功能需求列表中，针对第一个功能需求，请编写功能测试用例", context)
# # result3 = AgentManage.agent_chat(agent, "上一个问题是什么？", context)
# for i in result3:
#     if i.get("type") == "custom":
#         print(i.get("content"), end="", flush=True)
#     elif i.get("type") == "messages":
#         print(i.get("content"), end="", flush=True)

# ========== 第4轮：API 接口文档检索 ==========
print("=======================第4步：接口文档的检索和生成功能用例=====================================")
result4 = AgentManage.agent_chat(agent, "请给出登录接口的所有请求和响应信息，并生成接口测试用例", context)
for i in result4:
    if i.get("type") == "custom":
        # writer() 内容每条独立一行，自动换行
        print(i.get("content"), end="", flush=True)
    elif i.get("type") == "messages":
        # LLM token 流式输出，同一消息内不换行
        print(i.get("content"), end="", flush=True)
print("\n=============================第5步=========================================================")
print(f"所有长期记忆：{DualMemoryManager().load_long_term_memories(context)}")