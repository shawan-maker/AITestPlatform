from langgraph.store.memory import InMemoryStore
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

memory = InMemoryStore()

memory.put(("users","123456"), "old",{"user_name":"user1","description":"这是用户1"})
print("=================================第一次对话===========================================")
prompt = "我的名字是：石头，请记住我的名字"
response = llm.invoke(prompt)
print(response.content)
memory.put(("users","123456"), "user",{"user_name":"user1","description":response.content})
print("=================================第二次对话===========================================")
old_prompt = memory.get(("users","123456"), "user")
# print(old_prompt.value["description"])
new_prompt = [
    HumanMessage(content=old_prompt.value["description"]),
    HumanMessage(content="我的名字叫什么?")
]
response = llm.stream(new_prompt)
for chunk in response:
    print(chunk.content, end="",flush=True)