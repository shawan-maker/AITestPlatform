import dotenv
import os

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

# =============================================== 创建一个Agent ===============================================
# 1、创建一个Agent对象（Agent也是一个Runnable对象
agent = create_react_agent(
    model=llm,
    tools=[get_user_age, get_user_sex],
    prompt=prompt
    # output_parser=json_parser
)
# (1) invoke方式执行
# response = agent.invoke({"messages": [HumanMessage(content="我的名字叫张三")]})
# print(response)

# (2) stream方式 执行
# {"recursion_limit":10} 递归限制，防止无限递归
response = agent.stream({"messages": [HumanMessage(content="我的名字叫张三")]},{"recursion_limit":10})
for chunk in response:
    print(chunk)

# (3)  获取agent执行的流程图
# res = agent.get_graph().draw_mermaid_png()
# with open ("agent_graph.png", "wb") as f:
#     f.write(res)
