import dotenv
import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableBranch

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

# 对不同的用户输入，调用不同的模型
llm = RunnableBranch(
    (lambda x: x.get("gender") == "男", prompt | llm_ds | json_parser),
    (lambda x: x.get("gender") == "女", prompt | llm_qw | json_parser),
    llm_qw  # default runnable，当以上条件都不匹配时执行
)
# chain = prompt | llm | json_parser
response = llm.invoke({"name":"张三","gender":"男"})
print(response)