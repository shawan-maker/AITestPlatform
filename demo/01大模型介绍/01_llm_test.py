import dotenv
import os
from langchain_openai import ChatOpenAI

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

# （1）调用大模型（invokie方法，等待模型回复完成所有问题，才返回结果）
# response = llm.invoke("写一首五言绝句，主题是冬天")
# print(response)

# （2）调用大模型（stream方法，每行数据返回一个结果） - 流式返回
# response = llm.stream("写一首五言绝句，主题是冬天")
# for chunk in response:
#     print(chunk.content, end="",flush=True)

# （3）批量处理多个问题
# response = llm.batch([
#     "写一首五言绝句，主题是冬天",
#     "写一首五言绝句，主题是夏天"
# ])
response = llm.batch([
    "武汉今天最新的天气信息？",
    "苏州今天最新的天气信息？"
])
for chunk in response:
    print(chunk.content)