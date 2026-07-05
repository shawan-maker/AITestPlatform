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

class UserInfo(TypedDict):
    name: str
    age: str

@tool(description="获取用户信息")
def get_user_info(config:RunnableConfig):
    """获取用户信息"""
    print("正在获取用户信息...")
    user_id = config.get("configurable").get("user_id")
    thread_id = config.get("configurable").get("thread_id")
    store = get_store()
    userinfo = store.get((user_id,thread_id),"name")
    print("工具执行结果为：",userinfo.value)
    return userinfo

@tool(description="写入用户信息")
def add_user_info(userinfo:UserInfo,config:RunnableConfig):
    """写入用户信息"""
    print("正在写入用户信息...")
    store = get_store()
    user_id = config.get("configurable").get("user_id")
    thread_id = config.get("configurable").get("thread_id")
    store.put((user_id,thread_id),"name",dict(userinfo))
    return "用户信息写入成功"


agent = create_react_agent(
    model=llm,
    tools=[add_user_info,get_user_info],
    store=memory
)
print("=================================第一次对话===========================================")
resposne = agent.stream({"messages": [{"role": "user", "content": "我的用户信息是：石头，年龄11岁"}]},
             config={"configurable":{"user_id":"test123","thread_id":"shitou001"}},
                         stream_mode="messages")

for chunk,item in resposne:
    print(chunk.content,end="",flush=True)

print("=================================第二次对话===========================================")
resposne2 = agent.stream({"messages": [{"role": "user", "content": "请读取用户信息"}]},
             config={"configurable":{"user_id":"test123","thread_id":"shitou001"}},
                        stream_mode="messages")

for chunk,item in resposne2:
    print(chunk.content,end="",flush=True)