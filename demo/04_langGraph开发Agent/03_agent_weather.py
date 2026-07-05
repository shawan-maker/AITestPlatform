import dotenv
import os

import pymysql
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent



# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))
# 1. 定义天气查询工具
@tool(description="模拟天气查询工具")
def get_weather(city: str) -> str:
    """模拟天气查询工具"""
    weather_data = {
        "北京": {"temp": 22, "condition": "晴"},
        "上海": {"temp": 25, "condition": "多云"},
        "广州": {"temp": 28, "condition": "阵雨"}
    }
    if city in weather_data:
        return f"{city}天气：{weather_data[city]['condition']}，温度{weather_data[city]['temp']}℃"
    return f"找不到{city}的天气信息"

# 2. 创建基础代理
agent = create_react_agent(
    model=llm,  # 使用轻量级模型
    tools=[get_weather],
    prompt="你是一个专业的天气助手，请准确回答天气相关问题"
)

# 3. 测试查询
response = agent.stream(
    {"messages": [{"role": "user", "content": "北京天气怎么样？"}]}
)
for chunk in response:
    print(chunk)