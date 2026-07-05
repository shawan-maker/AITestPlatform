import dotenv
import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

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
    请分别调用get_user_age获取我的年龄, 
    调用get_user_sex工具获取我的性别信息，
    请帮我把个人信息转换为json格式输出，
    输出格式要求如下:
    {{"name":xx,"age":xx,"gender":xx}}
    """
)
json_parser = JsonOutputParser()

# (1) 装饰器定义工具函数
# 1.1 定义工具函数
@tool(description="获取年龄")
def get_user_age(name):
    """获取年龄"""
    return f"{name}的年龄是18"

@tool(description="获取性别")
def get_user_sex(name):
    """获取性别"""
    return f"{name}的性别是男"

# 1.2 绑定工具函数到大模型对象中
# llm_tool = llm.bind_tools(tools=(get_user_age, get_user_sex),tool_choice="get_user_sex")
llm_tool = llm.bind_tools(tools=(get_user_age, get_user_sex))



# 1.3 调用大模型工具函数
# 工具名称到工具函数的映射(这一步必须有，需要通过字典映射找到实际的工具函数对象，否则无法调用)
tools_map = {
    "get_user_age": get_user_age,
    "get_user_sex": get_user_sex
}
def function_calling(response):
    """调用工具"""
    tool_lists = response.tool_calls
    print("工具调用列表:",tool_lists)
    tool_call_res = []
    for tool_call in tool_lists:
        func_name = tool_call.get("name")
        args = tool_call.get("args")
        # 根据名称获取工具函数并调用
        func = tools_map[func_name]
        res = func.invoke(args)
        print(f"工具{func_name}调用结果为:",res)
        tool_call_res.append(res)
    return tool_call_res
# 定义工具函数为runnable对象（可以加入链式调用）
tool_run = RunnableLambda(function_calling)

# 1.4 重新调用大模型（invokie方法，输入包括 用户输入 + 工具函数输出，等待模型回复完成所有问题，才返回结果）
def get_final_result(tool_result):
    """获取结果"""
    prompt_res  = prompt.invoke({"name":"张三"})
    new_prompt = str(prompt_res) + "\n" + str(tool_result)
    return llm.invoke(new_prompt)

get_result = RunnableLambda(get_final_result)

chain = prompt | llm_tool | tool_run | get_result | json_parser
response = chain.invoke({"name":"张三"})
# print(response.tool_calls)
print(response)