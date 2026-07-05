import dotenv
import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableBranch, RunnableMap

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、deepseek大模型
llm_ds = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

# 2、千问大模型
llm_qw = ChatOpenAI(model_name=os.getenv("QW_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

# 2、ChatPromptTemplate提示词模版
prompt = PromptTemplate(
    input_variables=["name","gender"],
    template="""
    我的名字叫{name}，年龄是18，性别是{gender}
    请帮我把个人信息转换为json格式输出，
    输出格式要求如下:
    {{"name":xx,"age":xx,"gender":xx}}
    """
)
json_parser = JsonOutputParser()

llm1 = prompt | llm_ds | json_parser
llm2 = prompt | llm_qw | json_parser

paralle_chain = RunnableMap({
    "deepseek": llm1,
    "qwen": llm2
})

response = paralle_chain.invoke({"name":"张三","gender":"男"})
print("deepseek:",response["deepseek"])
print("qwen:",response["qwen"])