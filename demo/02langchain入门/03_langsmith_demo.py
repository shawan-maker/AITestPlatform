import dotenv
import os
from langchain_openai import ChatOpenAI

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

prompt = [
    {"role": "system", "content": "你是一个宋代的诗人，你需要根据给定的主题，写一首五言绝句。"},
    {"role": "user", "content": "你好，请帮我写一首五言绝句，主题是冬天"}
]

# prompt = [
#     {"role": "user", "content": """请逐步分析登录功能的测试点，
#     按以下逻辑展开：
#     1. 识别输入字段（用户名/密码）
#     2. 列出每个字段的合法/非法输入情况
#     3. 分析页面交互流程（按钮状态、错误提示等）
#     最终输出结构化测试点列表"""}
# ]

response = llm.stream(prompt)
for chunk in response:
    print(chunk.content, end="",flush=True)