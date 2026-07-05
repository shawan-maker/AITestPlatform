import dotenv
import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

# 3、ChatPromptTemplate提示词模版
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的助手。请根据用户的姓名，调用相应的工具获取用户的年龄和性别信息，并将结果以JSON格式输出。输出格式: {{'name':xx,'age':xx,'gender':xx}}"),
    MessagesPlaceholder(variable_name="messages")
])
json_parser = JsonOutputParser()

# 4、装饰器定义工具函数
@tool(description="获取年龄")
def get_user_age(name):
    """获取年龄"""
    return f"{name}的年龄是18"

@tool(description="获取性别")
def get_user_sex(name):
    """获取性别"""
    return f"{name}的性别是男"

# =============================================== 定义检查点 ===============================================
checkpointer = InMemorySaver()

# =============================================== 创建一个Agent ===============================================
# 1、创建一个Agent对象（Agent也是一个Runnable对象
agent = create_react_agent(
    model=llm,
    tools=[get_user_age, get_user_sex],
    prompt=prompt,
    checkpointer=checkpointer
    # output_parser=json_parser
)

# (2) stream方式 执行
config = {"configurable":{"thread_id":"1"}}
response = agent.stream({"messages": [HumanMessage(content="我的名字叫张三")]},config=config)
# for chunk in response:
#     for node_data in chunk.values():
#         for msg in node_data["messages"]:
#             print(msg.content)
print("=================================打印对话内容===========================================")
for chunk in response:
    print(chunk)

# 打印对话内容时，实际是针对最新的节点镜像，进行迭代器的打印（每一次打印都是一个对话消息，共同组合完整的对话 - 最新的节点镜像）
# 打印检查点内容时，实际是针对所有的节点镜像，进行迭代器的打印（每一次打印都是一个节点镜像，后面的镜像包括前面的所有内容）

print("=================================打印检查点内容===========================================")
result = list(agent.get_state_history(config=config))[::-1]
for state in result:
    print(f"当前执行的上下文为：{state.config}")
    print(f"当前执行的值为：{state.values}")
    print(f"下一个执行的节点为:{state.next}")
