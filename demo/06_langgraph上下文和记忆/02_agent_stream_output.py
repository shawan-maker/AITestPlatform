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
from langgraph.config import get_stream_writer

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")

# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

# 3、ChatPromptTemplate提示词模版
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个资深的dba工程师,请根据用户的要求,生成sql语句,并调用工具执行sql语句,并将结果以JSON格式输出。
    重要提示：
    1. 创建表时，所有时间字段必须使用 TIMESTAMP 类型，不能使用 DATETIME
    2. TIMESTAMP 类型的默认时间设置为 DEFAULT CURRENT_TIMESTAMP
    3. 避免使用过于复杂的表结构，保持简洁实用"""),
    MessagesPlaceholder(variable_name="messages")
])
json_parser = JsonOutputParser()

# 4、装饰器定义工具函数
@tool(description="连接数据库,并执行sql语句")
def execute_sql(sql):
    """执行sql语句"""
    writer = get_stream_writer()
    conn = pymysql.connect(host="127.0.0.1", user="root", password="root", database="test",autocommit=True)
    cursor = conn.cursor()
    writer("正在执行sql语句：{}".format(sql))
    cursor.execute(sql)
    result = cursor.fetchall()
    return result

# =============================================== 创建一个Agent ===============================================
# 1、创建一个Agent对象（Agent也是一个Runnable对象
agent = create_react_agent(
    model=llm,
    tools=[execute_sql],
    prompt=prompt
)
# (1) stream方式执行
# 输入一个任务
input_text = """
需要你设计一个图书管理系统的用户表(Users4)
先判断表是否存在，如果不存在则先调用数据库操作工具在进行建表,如果存在则跳过建表操作
然后再生成2条数据，通过sql语句添加到用户表中(注意不要数据重复)
将用户表中的所有数据的real_name、user_type、status查询出来，并以json格式输出
"""
response = agent.stream({"messages": [HumanMessage(content=input_text)]},
                        stream_mode=["updates", "custom"])
# (2) stream_mode="messages"
# for item,chunk in response:
#     print(chunk.content,end="",flush=True)

for type,chunk in response:
    if type == "custom":
        print(f"{type} —— {chunk}")
    elif type == "updates":
        for node_data in chunk.values():
            for message in node_data.get('messages', []):
                if hasattr(message, 'content'):
                    print(f"{type} —— {message.content}", flush=True)