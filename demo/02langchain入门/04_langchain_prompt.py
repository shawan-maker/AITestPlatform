import dotenv
import os

from langchain_core.prompts import PromptTemplate,FewShotPromptTemplate,ChatPromptTemplate,MessagesPlaceholder
from langchain_openai import ChatOpenAI

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))
#
# # 1、创建一个提示词模版
# prompt = PromptTemplate(
#     input_variables=["topic"],
#     template="""
#     你是一个{period}时期的诗人，
#     请根据给定的主题，写一首五言绝句。主题是：{topic}"""
#
# )
# prompt.format(period="盛唐",topic="国家")
# print(prompt.format(period="盛唐",topic="国家"))


# # 2、创建一个带样本的提示词模版
# examples = [
#     {"input": "点击登录按钮无反应", "output": "功能缺失"},
#     {"input": "加载页面卡顿超过10秒", "output": "性能问题"}
# ]
#
# example_prompt = PromptTemplate(
#     input_variables=["input", "output"],
#     template="Bug描述：{input}\nBug类型：{output}"
# )
#
# few_shot_prompt = FewShotPromptTemplate(
#     # 样本
#     examples=examples,
#     # 样板格式
#     example_prompt=example_prompt,
#     # 提示词最前的一句话
#     prefix="请根据以下示例判断Bug类型：",
#     # 提示词最后面的一句话
#     suffix="Bug描述：{user_input}\nBug类型：",
#     # 用户输入的变量
#     input_variables=["user_input"]
# )
# print(few_shot_prompt.format(user_input="用户头像无法上传"))

# #3、创建一个多轮对话的提示词模版
chat_template = ChatPromptTemplate([
    ("system", "你是一个{period}时期的诗人"),
    ("human", "请根据给定的主题，写一首五言绝句。主题是：{topic}"),
    ("system", "你是一个{period}时期的主考官"),
    ("human", "请从以下诗句中，选出一首最符合{topic}的诗句：{poems}"),
    ],
    input_variables=["period", "topic", "poems"]
)
print(chat_template.format(period="盛唐",topic="国家",poems="中国是ilen的"))

# # 4、创建的一个langchain的语言表达式
chain = chat_template | llm
response = chain.invoke({"period":"盛唐", "topic":"国家", "poems":"中国是ilen的"})
print(response.content)