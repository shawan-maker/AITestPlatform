import dotenv
import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

# 2、ChatPromptTemplate提示词模版
prompt = PromptTemplate(
    input_variables=["name"],
    template="""
    我的名字叫{name}，年龄是18，性别是男
    请帮我把个人信息转换为json格式输出，
    输出格式要求如下:
    {{"name":xx,"age":xx,"gender":xx}}
    """
)
json_parser = JsonOutputParser()

#  -----------------------------------自定义的函数，声明为runnable对象,就可以加入链式调用 -----------------------------------------------------
# # (1) 简单函数使用lambda表达式定义
# runable = RunnableLambda(lambda x: x.get("name"))
# (2) 复杂函数使用普通函数定义
def get_user_info(x):
    return [x.get("name"), x.get("age"), x.get("gender")]
runable = RunnableLambda(get_user_info)

chain = prompt | llm | json_parser | runable
# 调用大模型（invokie方法，等待模型回复完成所有问题，才返回结果）
response = chain.invoke({"name":"张三"})
print(response)