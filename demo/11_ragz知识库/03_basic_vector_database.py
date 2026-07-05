from langchain_community.vectorstores import FAISS
import dotenv
import os

from langchain_core.documents import Document
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

# 3、准备document对象的数据（同切片后返回的对象一致）
data = ["我是python程序员，我会python开发",
                                 "我是java程序员，我会java开发",
                                 "我是c++程序员，我会c++开发"]
document_data = [Document(page_content=item) for item in data]

# 4、 创建一个FAISS向量数据库对象
faiss = FAISS.from_documents(document_data, embedding)
faiss.add_texts(["我是测试工程师，我会写测试脚本"])
# 从向量数据库中搜索出内容
query = "测试脚本"
result = faiss.similarity_search(query, 1)
print(result)

"""
语义检索的准确率（召回率）：
rag：
    检索： 基于语义去向量数据库查找向量计算之后距离最近的K个结果 (该脚本实现了这一步)
    上下文增强： 把检索出来的K个结果，按照特定的规则进行排序和过滤
    生成：将检索出的K个结果和最初的问题给到大模型，由大模型去基于检索结果和用户问题去生成一个答案 
"""
