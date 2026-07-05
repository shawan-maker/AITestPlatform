import dotenv
import os
from langchain_openai import OpenAIEmbeddings

"""
 搭建知识库：
 1、相关的文档进行向量化处理，并存储到向量数据库中
     - 如果文档内容过大，需要进行切片处理，并分别进行向量化处理，并存储到向量数据库中
     - 如果文档内容过小，可以直接进行向量化处理，并存储到向量数据库中
2、
"""

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")

# 2、调用OpenAIEmbeddings生成嵌入式模式对象
embedding = OpenAIEmbeddings(model="Qwen/Qwen3-Embedding-8B",
                       api_key=os.getenv("SI_API_KEY"),
                       base_url=os.getenv("SI_BASE_URL"))

# 3、调用embed_documents接口，将文本进行向量化存储
embedding.embed_documents(["我是python程序员，我会python开发",
                                 "我是java程序员，我会java开发",
                                 "我是c++程序员，我会c++开发"])

# 4、调用embed_query接口，将文本进行向量化检索
res = embedding.embed_query("我是python程序员")
print(res)