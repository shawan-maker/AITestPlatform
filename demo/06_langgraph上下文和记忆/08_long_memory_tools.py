from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langmem import create_manage_memory_tool, create_search_memory_tool
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

agent = create_react_agent(
    model=llm,
    tools=[
        # 创建一个长期记忆的管理工具
        create_manage_memory_tool(("user_id","thread_id")),
        # 创建一个长期记忆的搜索工具
        create_search_memory_tool(("user_id","thread_id"))
    ],
    store=memory
)

resposne = agent.stream({"messages": [{"role": "user", "content": "我的用户信息是：石头，年龄11岁,请使用记忆管理工具进行存储"}]},
             config={"configurable":{"user_id":"test123","thread_id":"shitou001"}},
                         stream_mode="messages")

for chunk,item in resposne:
    print(chunk.content,end="",flush=True)

print("=================================第二次对话===========================================")
resposne2 = agent.stream({"messages": [{"role": "user", "content": "请从记忆管理工具中，查看我的名字和年龄是什么?"}]},
             config={"configurable":{"user_id":"test123","thread_id":"shitou001"}},
                        stream_mode="messages")

for chunk,item in resposne2:
    print(chunk.content,end="",flush=True)