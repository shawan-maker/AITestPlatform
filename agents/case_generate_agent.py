"""
case_generate_agent.py
        1、 封装langchain的工具或者开发MCP服务
            - 调用rag系统，去知识库中检索需求文档（扩展优化封装一个专门用于需求和文档检索的Agent：包括：知识库检索，数据检索）
            - 用例生成的工具
        2、 创建Agent，设计Agent的决策提示词
        3、 调用Agent完成用例生成

架构说明：
    双记忆系统（详见 agents.memory.manager.DualMemoryManager）：
    - Checkpointer (InMemorySaver):     单次会话内多轮交互的自动存储（短期/工作记忆）
    - InMemoryStore:                    不同对话之间的跨会话记忆存储（长期/结论记忆）

    数据流：
        新会话首次 → InMemoryStore 读长期记忆 → 注入 system message
        → checkpointer(thread_id) 自动管理本会话多轮
        → 每轮结束 → LLM 提取摘要 → 写入 InMemoryStore（异步后台执行）
"""

import asyncio
import os, dotenv

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from config.prompts.agents import case_generate_agent_prompt, api_case_generate_agent_prompt, main_agent_prompt
from config.settings import llm
from mcp_tools.tools import (
    search_requirement,
    generate_testcases,
    search_api_document,
    generate_base_cases,
    api_document_to_cases,
    load_evn_data,
)
# 引入双记忆系统模块：DualMemoryManager（管理读写逻辑）+ RuntimeContext（运行时上下文）
from agents.memory.manager import DualMemoryManager, RuntimeContext
from service.core.async_utils import run_on_main_loop


class AgentManage:
    """Agent管理类"""

    @staticmethod
    def create_case_generate_agent():
        """创建功能测试用例生成的 Agent（挂载 checkeeper 用于短期多轮记忆）"""
        # 从 DualMemoryManager 获取全局单例 checkpointer
        memory = DualMemoryManager()
        agent = create_react_agent(
            name="case_generate_agent",
            model=llm,
            tools=[search_requirement, generate_testcases],
            prompt=case_generate_agent_prompt.prompt,
            checkpointer=memory.checkpointer,
        )
        return agent

    @staticmethod
    def create_functional_generate_agent():
        """创建不含 search_requirement 的轻量手工用例生成 Agent（用于无文档场景）"""
        memory = DualMemoryManager()
        agent = create_react_agent(
            name="functional_generate_agent",
            model=llm,
            tools=[generate_testcases],
            prompt=case_generate_agent_prompt.prompt,
            checkpointer=memory.checkpointer,
        )
        return agent

    @staticmethod
    def create_api_case_generate_agent():
        """创建API测试用例生成的 Agent"""
        memory = DualMemoryManager()
        agent = create_react_agent(
            name="api_case_generate_agent",
            model=llm,
            tools=[search_api_document, generate_base_cases],
            prompt=api_case_generate_agent_prompt.prompt,
            checkpointer=memory.checkpointer,
        )
        return agent

    @classmethod
    def create_supervisor_agent(cls):
        """创建一个主管的多 Agent 程序（supervisor 协调各子 Agent 分工）"""
        memory = DualMemoryManager()
        supervisor = create_supervisor(
            agents=[cls.create_case_generate_agent(), cls.create_api_case_generate_agent()],
            model=llm,
            prompt=main_agent_prompt.prompt,
            output_mode="full_history",  # 保留完整对话历史，确保 checkpointer 能积累上下文
        ).compile(
            checkpointer=memory.checkpointer,
        )
        return supervisor

    @staticmethod
    def agent_chat(agent, query: str, context: RuntimeContext, run_config: dict | None = None):
        """Agent 对话入口 —— 整合双记忆系统的完整对话流程
        
        Yields:
            {"type": "custom" | "messages" | "tool_call", "content": str, "tool_name": optional}
        """
        memory = DualMemoryManager()

        # 通过 run_on_main_loop 将协程安全调度到主事件循环，
        # 避免 asyncio.run() 创建/销毁事件循环导致 ORM 连接池损坏
        input_data = run_on_main_loop(memory.prepare_messages(context, query))

        config = run_config or {"configurable": {"thread_id": context.thread_id}}
        if "configurable" not in config:
            config["configurable"] = {"thread_id": context.thread_id}
        elif "thread_id" not in config["configurable"]:
            config["configurable"]["thread_id"] = context.thread_id

        response = agent.stream(
            input=input_data,
            subgraphs=True,
            stream_mode=["messages", "custom", "tool_call"],
            config=config,
            context={
                "project_name": context.project_name,
                "module_id": context.module_id,
            },
        )

        result_parts = []
        for chunk in response:
            if chunk[1] == "custom":
                raw_data = chunk[2]
                if isinstance(raw_data, list):
                    content = "".join(str(item) for item in raw_data)
                else:
                    content = str(raw_data)
                result_parts.append(content)
                yield {"type": "custom", "content": content}
            elif chunk[1] == "messages":
                content = chunk[2][0].content
                result_parts.append(content)
                yield {"type": "messages", "content": content}
            elif chunk[1] == "tool_call":
                tool_chunk = chunk[2]
                tool_name = getattr(tool_chunk, "name", None) or str(tool_chunk)
                content = str(tool_chunk)
                yield {"type": "tool_call", "content": content, "tool_name": tool_name}

        full_result = "".join(result_parts)
        if full_result.strip():
            run_on_main_loop(memory.save_after_turn(context, query, full_result))


if __name__ == '__main__':
    # ============================================================
    # 主函数测试入口 —— 验证双记忆系统的完整链路
    # ============================================================
    agent = AgentManage.create_supervisor_agent()

    # 创建运行上下文参数（标识一次对话的全部维度）
    context = RuntimeContext(
        project_name="p2p金融项目",
        module_id="login001",
        user_id="user001",
        session_id="session001",
        thread_id="thread_001"     # 注意：每个新会话应使用不同的 thread_id
    )

    print("=======================接口文档的检索和生成功能用例=====================================")
    result4 = AgentManage.agent_chat(agent, "请给出登录接口的所有请求和响应信息，并生成接口测试用例", context)
    for i in result4:
        if i.get("type") == "custom":
            # writer() 内容每条独立一行，自动换行
            print(i.get("content"), end="\n", flush=True)
        elif i.get("type") == "messages":
            # LLM token 流式输出，同一消息内不换行
            print(i.get("content"), end="", flush=True)

    # 多轮测试示例（同一 thread_id 下，第2轮将自动复用短期记忆 + 仅首次注入长期记忆）
    # print("=======================第2步=====================================")
    # result5 = AgentManage.agent_chat(agent, "基于上面的登录接口，生成测试用例", context)
    # for i in result5:
    #     if i.get("type") == "custom":
    #         print(i.get("content"), end="", flush=True)
    #     elif i.get("type") == "messages":
    #         print(i.get("content"), end="", flush=True)
