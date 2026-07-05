"""
03_workflow_and_RAG.py
    —— 已实现：将rag知识库接入到工作流中
    —— 特点： 工作流的执行流程是固定的

下一步实现：将rag知识库接入到用例生成的Agent中
    —— 特点：执行步骤更留货，根据当前的情况动态去规划下一步的任务进行执行
    —— 步骤：
        1、 封装langchain的工具或者开发MCP服务
            - 调用rag系统，去知识库中检索需求文档（扩展优化封装一个专门用于需求和文档检索的Agent：包括：知识库检索，数据检索）
            - 用例生成的工具
        2、 创建Agent，设计Agent的决策提示词
        3、 调用Agent完成用例生成

"""
import asyncio
import os,dotenv

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from demo.CaseGenerateAgent.RAG_Anything import _base_dir
from demo.CaseGenerateAgent.Agents.tools import search_requirement, generate_testcases
from langgraph.checkpoint.memory import InMemorySaver

# 加载env文件到环境变量
dotenv.load_dotenv(os.path.join(_base_dir, ".env"))
# 调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("LLM_MODEL"),
                 openai_api_key=os.getenv("LLM_BINDING_API_KEY"),
                 openai_api_base=os.getenv("LLM_BINDING_HOST"))
checkpointer = InMemorySaver()

async def main():
    # 创建Agent
    agent = create_react_agent(
        model=llm,
        tools=[search_requirement, generate_testcases],
        prompt="""
             你是一个智能测试用例生成 Agent，目标是根据用户需求生成高质量的测试用例。  
                你运行在一个 MCP 服务中，拥有以下工具：  
                1. search_requirement：  
                   - 输入：功能描述或需求关键词  
                   - 输出：与之相关的需求说明文档或片段  
                   - 用途：帮助你在生成测试用例前获取或确认需求背景  
                
                2. generate_testcases：  
                   - 输入：需求说明（功能点、约束、业务规则等）  
                   - 输出：系统化的测试用例集，包括前置条件、测试步骤、期望结果  
                   - 用途：根据需求说明生成测试用例
                
                ### 工作原则
                - 当用户输入模糊或缺乏上下文时，先调用 **search_requirement** 获取相关需求信息。  
                - 当需求信息明确时，调用 **generate_testcases** 生成测试用例。  
                - 如果检索结果仍然不足以生成用例，应要求用户补充更多上下文。  
    
                ### 输出要求
                - 保持专业、简洁、工程化。  
                - 不要杜撰需求，必须基于真实检索结果或用户提供的信息。  
                - 如果遇到模糊情况，明确提示用户需要补充说明。  
            """,
        checkpointer=checkpointer,
    )

    response = agent.stream(
        input={
            "messages": [
                HumanMessage(content="用户需求：用户注册功能,生成测试用例")
            ]
        },
        stream_mode=["messages","custom"],
        config={"configurable": {"thread_id": "1"}},
        context={"project_name":"project02"}
    )

    for chunk in response:
        if chunk[0]=="custom":
            print(chunk[1])
        elif chunk[0]=="messages":
            print(chunk[1][0].content,end="",flush=True)

if __name__ == '__main__':
    asyncio.run(main())