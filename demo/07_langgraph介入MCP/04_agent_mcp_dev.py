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
        "mcp_dev": {
            "url": "http://127.0.0.1:8000/mcp",
            "transport": "streamable_http"
        }
    }
)

async def main():
    # 异步获取工具列表
    tools = await mcp_client.get_tools()
    print(f"工具列表：{tools}")
    resource = await mcp_client.get_resources("mcp_dev", uris=["file:///.env"])
    print(f"资源列表：{resource}")
    for blob in resource:
        print(blob.as_string())
    prompt = await mcp_client.get_prompt("mcp_dev","debug_errorr",arguments={"error": "mcp.shared.exceptions.McpError: Missing required arguments"})
    print(f"提示列表：{prompt}")

if __name__ == "__main__":
    asyncio.run(main())