import dotenv
import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.runtime import get_runtime
from dataclasses import dataclass

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

@dataclass
class ContextSchema:
    user_name: str

# 用于构建 system prompt 的函数
def prompt(state):
    runtime = get_runtime(ContextSchema)
    user = runtime.context.user_name
    return [{"role": "system", "content": f"Hello {user}!"}, *state["messages"]]

# 创建 agent 时声明上下文 schema
agent = create_react_agent(
    model=llm,
    tools=[],
    prompt=prompt,
    context_schema=ContextSchema
)

# 传入上下文
response = agent.stream(
    {"messages": [{"role": "user", "content": "Hi"}]},
    context={"user_name": "John Smith"},
    stream_mode="messages"
)

for chunk,metadata in response:
    print(chunk.content,end='',flush=True)