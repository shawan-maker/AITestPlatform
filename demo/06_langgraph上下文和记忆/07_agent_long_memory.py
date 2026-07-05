from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing_extensions import TypedDict

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.config import get_store
from langgraph.prebuilt import create_react_agent
from langgraph.store.memory import InMemoryStore
import dotenv
import os
from langchain_openai import ChatOpenAI

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")

# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

memory = InMemoryStore()

@tool(description="加法运算")
def add(a: int, b: int):
    """加法运算"""
    print("正在执行加法运算：{} + {}".format(a, b))
    store = get_store()
    store.put(("history",),"question", {"question":f"请计算{a}+{b}", "answer": f"{a+b}", "description": f"这是一个加法运算，计算{a} + {b}的结果"})
    return a + b

@tool(description="获取历史问题")
def get_history():
    """获取历史问题"""
    store = get_store()
    history = store.get(("history",),"question")
    if history:
        return f"上一个问题是：{history.value['question']}，答案是：{history.value['answer']}"
    else:
        return "没有找到历史记录"

agent = create_react_agent(
    model=llm,
    tools=[add, get_history],
    prompt=ChatPromptTemplate.from_messages([
        ("system", "你是一个计算器，请根据用户输入的加法运算，计算结果并返回结果。如果用户询问历史问题，使用get_history工具获取。"),
        MessagesPlaceholder(variable_name="messages")
    ]),
    store=memory
)
print("=================================第一次对话===========================================")
response = agent.stream({"messages": [HumanMessage(content="请计算1+2")]},stream_mode="messages")
for chunk,metadata in response:
    print(chunk.content,end="",flush=True)
print("=================================第二次对话===========================================")
response = agent.stream({"messages": [HumanMessage(content="请问我上一个问题是什么")]},stream_mode="messages")
for chunk,metadata in response:
    print(chunk.content,end="",flush=True)