import os

import dotenv
from langchain_openai import ChatOpenAI

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# env配置文件路径
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")
# 加载env文件到环境变量
dotenv.load_dotenv(ENV_FILE_PATH)

# RAG配置
# 内存输出路径
OUTPUT_DIR = os.path.join(BASE_DIR, "rag","output")
# RAG_STORAGE存储路径
RAG_MANAGE_STORAGE = os.path.join(BASE_DIR, "rag","rag_storage")
# 学习文档的存储路径
DOCUMENT_DIR = os.path.join(BASE_DIR, "rag","document")

# RAG服务的配置
RAG_SERVER_URL=os.getenv("RAG_SERVER_URL")
RAG_API_KEY=os.getenv("RAG_API_KEY")

# 调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("LLM_MODEL"),
                 openai_api_key=os.getenv("LLM_BINDING_API_KEY"),
                 openai_api_base=os.getenv("LLM_BINDING_HOST"))

# 配置生成可执行接口用例的最大重试次数
MAX_GENERATOR_COUNT = 3
# 配置生成可执行接口用例的批次大小
MAX_BATCH_SIZE = 5