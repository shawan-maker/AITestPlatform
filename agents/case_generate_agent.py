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
from mcp_tools.tools import search_requirement, generate_testcases, search_api_document, api_document_to_cases, \
    load_evn_data
# 引入双记忆系统模块：DualMemoryManager（管理读写逻辑）+ RuntimeContext（运行时上下文）
from agents.memory.manager import DualMemoryManager, RuntimeContext


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
    def create_api_case_generate_agent():
        """创建API测试用例生成的 Agent"""
        memory = DualMemoryManager()
        agent = create_react_agent(
            name="api_case_generate_agent",
            model=llm,
            tools=[search_api_document,load_evn_data,api_document_to_cases],
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
    def agent_chat(agent, query: str, context: RuntimeContext):
        """Agent 对话入口 —— 整合双记忆系统的完整对话流程
        
        流程概览：
          Step 1: 准备消息（自动处理长期记忆注入 + 去重控制）
          Step 2: 流式调用 Agent（checkeeper 自动管理本会话内短期多轮）
          Step 3: 后台异步保存长期记忆摘要（每轮都执行，不阻塞主流程）
        
        Args:
            agent:   已编译的 supervisor 或子 agent 实例
            query:   用户本轮输入
            context: 运行上下文（包含 project/module/user/session/thread 维度信息）
        
        Yields:
            {"type": "custom" | "messages", "content": str} 格式的流式输出块
        """
        memory = DualMemoryManager()

        # ========== Step 1: 准备输入消息（含长期记忆注入） ==========
        # 内部逻辑：按 thread_id 判断是否需要注入 → 加载 InMemoryStore 历史 → 组装 SystemMessage
        input_data = asyncio.run(memory.prepare_messages(context, query))

        # ========== Step 2: 执行 Agent 流式响应 ==========
        response = agent.stream(
            input=input_data,
            subgraphs=True,
            stream_mode=["messages", "custom","tool_call"],
            config={"configurable": {"thread_id": context.thread_id}},
            context={
                "project_name": context.project_name,
                "module_id": context.module_id
            }
        )

        result_parts = []       # 收集完整回答内容，用于后续保存
        for chunk in response:
            if chunk[1] == "custom":
                raw_data = chunk[2]
                # ★ 类型安全处理：custom 类型可能是 str 或 list
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

        # ========== Step 3: 后台异步保存长期记忆 ==========
        full_result = "".join(result_parts)
        if full_result.strip():
            # 流式输出已收集完毕，使用 asyncio.run 执行保存（无需事件循环）
            # 内部流程：LLM提取摘要 → 失败则降级兜底 → 写入 InMemoryStore
            asyncio.run(memory.save_after_turn(context, query, full_result))


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
