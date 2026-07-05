from typing import Type

import dotenv
import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool, BaseTool

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
    我的名字叫{name}
    请分别调用get_user_age获取我的年龄, get_user_sex工具获取我的性别信息，
    请帮我把个人信息转换为json格式输出，
    输出格式要求如下:
    {{"name":xx,"age":xx,"gender":xx}}
    """
)
json_parser = JsonOutputParser()

# 1.1 定义工具函数
# # (1) 装饰器定义工具函数
# @tool
# def get_user_age(name):
#     """获取年龄"""
#     return f"{name}的年龄是18"
#
# @tool
# def get_user_sex(name):
#     """获取性别"""
#     return f"{name}的性别是男"
# # 1.2 绑定工具函数到大模型对象中
# llm_tool = llm.bind_tools(tools=[get_user_age, get_user_sex])
# chain = prompt | llm_tool
# response = chain.invoke({"name":"张三"})
# print(response.tool_calls)

# (2) 集成BaseTool类定义工具函数
"""工具的名称、描述、参数都需要说明，否则大模型不知道调用谁"""
from pydantic import BaseModel,Field
class UserInfo(BaseModel):
    name:str = Field(description="姓名")

class get_user_age_tool(BaseTool):
    """获取年龄"""
    name:str = "get_user_age"
    description:str = "获取年龄"
    args_schema:Type[BaseModel] = UserInfo
    def _run(self, name):
        return f"{name}的年龄是18"

class get_user_sex_tool(BaseTool):
    """获取性别"""
    name:str = "get_user_sex"
    description:str = "获取性别"
    args_schema:Type[BaseModel] = UserInfo
    def _run(self, name):
        return f"{name}的性别是男"
# 1.2 绑定工具函数到大模型对象中
user_tool = get_user_age_tool()
response = user_tool.invoke({"name":"张三"})
print(response)

