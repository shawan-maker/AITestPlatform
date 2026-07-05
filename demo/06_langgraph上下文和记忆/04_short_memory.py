import dotenv
import os

import pymysql
from typing import Annotated

from langchain.agents import AgentState
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import create_react_agent
from langgraph.config import get_stream_writer
from langgraph.types import Command

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")

# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

class CustomState(AgentState):
    user_name: str
    remaining_steps: int

@tool(description="获取用户名")
def get_user_name(state: CustomState):
    username = state.get("user_name")
    if username == 'user123':
        return "用户名是：{}".format(username)
    else:
        return "用户名是：石头"

@tool(description="修改用户名")
def modify_user_name(new_name: str, state: CustomState, tool_call_id: Annotated[str, InjectedToolCallId]):
    print(f"修改前的用户名是：{state.get('user_name')}")
    # state.setdefault("user_name", new_name)
    return Command(update={
            "user_name": new_name,
            "messages":[
                ToolMessage(
                    "用户名修改成功！",
                    tool_call_id = tool_call_id
                )
            ]
        }
    )

agent = create_react_agent(
    model=llm,
    tools=[get_user_name,modify_user_name],
    state_schema=CustomState,
    prompt=ChatPromptTemplate.from_messages([
        ("system", "你是一个智能助手，你需要根据用户的指令进行操作"),
        MessagesPlaceholder(variable_name="messages"),
    ]),
)

response = agent.stream({"messages": [HumanMessage(content="请获取用户名,再修改用户名为user123，最后获取用户名")], "user_name": "test"},stream_mode="messages")

for chunk,item in response:
    print(chunk.content,end="",flush=True)