from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser, CommaSeparatedListOutputParser, PydanticOutputParser
from pydantic import BaseModel
import dotenv,os
dotenv.load_dotenv("../.env")



# 1、ChatOpenAI大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))


"""-----------------------------------------------json数据格式解析----------------------------------------"""
# # 2、ChatPromptTemplate提示词模版
# prompt = PromptTemplate(
#     input_variables=["name"],
#     template="""
#     我的名字叫{name}，年龄是18，性别是男
#     请帮我把个人信息转换为json格式输出，
#     输出格式要求如下:
#     {{"name":xx,"age":xx,"sex":xx}}
#     """
# )
#
# #| 3、jsonOutputParser输出解析器
# # class UserInfo(BaseModel):
# #     name: str
# #     age: int
# #     sex: str
# #
# # user_info_parser = JsonOutputParser(pydantic_model=UserInfo)
#
# # 可以直接使用BaseModel来解析json格式数据，不需要定义一个pydantic模型
# user_info_parser = JsonOutputParser()
#
# # (1)使用llm模型调用prompt模版，返回的结果为字符串
# # response = llm.invoke(prompt.format(name="张三"))
# # print(response.content,type(response.content))
#
# # (2)使用chain链来调用prompt模版和llm模型，并进行json格式化输出
# chain = prompt | llm | user_info_parser
# response = chain.invoke({"name":"张三"})
# print(response,type(response))

"""-----------------------------------------------解析成列表格式----------------------------------------"""
# response = llm.invoke('列出3种适合春季穿搭的颜色，用逗号分隔。')
# print("原始输出：", response.content)
# # 使用CommaSeparatedListOutputParser解析成列表格式，用逗号分隔
# list_parser = CommaSeparatedListOutputParser()
# response = list_parser.parse(response.content)
# print("解析后输出：", response)

"""-----------------------------------------------按照期望的格式输出----------------------------------------"""

# 2、ChatPromptTemplate提示词模版
prompt = PromptTemplate(
    input_variables=["name","output_format"],
    template="""
    我的名字叫{name}，年龄是18，性别是男
    请帮我把个人信息转换为json格式输出，
    输出格式要求如下:
    {output_format}
    """
)
class UserInfo(BaseModel):
    name: str
    age: int
    gender: str

user_info_parser = PydanticOutputParser(pydantic_object=UserInfo)
# 获取格式化后的json格式
output_format = user_info_parser.get_format_instructions()
# 定义一个chain链
chain = prompt | llm | user_info_parser
response = chain.invoke({"name":"张三","output_format":output_format})
print(response,type(response))
print(response.name,response.age,response.gender)
