import dotenv
import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient



# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

# 3、接入mcp服务
mcp_client = MultiServerMCPClient(
    {
        "mcp_demo": {
            "url": "http://127.0.0.1:8000/mcp",
            "transport": "streamable_http"
        }
    }
)

async def main():
    # 异步获取工具列表
    tools = await mcp_client.get_tools()

    # 4. 创建基础代理
    agent = create_react_agent(
        model=llm,  # 使用轻量级模型
        tools=tools,
        prompt="你是一个专业的天气助手，请准确回答天气相关问题"
    )

    # 3. 测试查询
    print("=================================第一次对话===========================================")
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "1加100是多少？"}]}
    )
    messages = response.get('messages', [])
    for msg in messages:
        role = type(msg).__name__  # HumanMessage / AIMessage / ToolMessa+ge
        content = msg.content
        # ToolMessage 的 content 可能是列表格式
        if isinstance(content, list):
            content = "".join(item.get('text', '') for item in content if item.get('type') == 'text')
        print(f"[{role}]: {content}")

if __name__ == "__main__":
    asyncio.run(main())