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
# request_timeout: 单次 LLM API 请求超时(秒)，防止 agent.stream() 永久阻塞
# max_tokens: 单次 LLM 最大输出 token 数（接口文档解析等长输出场景需足够大）
# max_retries: 自动重试次数
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "gpt-4o"),
    api_key=os.getenv("LLM_BINDING_API_KEY"),
    base_url=os.getenv("LLM_BINDING_HOST"),
    request_timeout=int(os.getenv("LLM_REQUEST_TIMEOUT", "120")),
    max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
    max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
)

# 配置生成可执行接口用例的最大重试次数
MAX_GENERATOR_COUNT = 3
# 配置生成可执行接口用例的批次大小
MAX_BATCH_SIZE = 5
# 基础用例覆盖率不足时，complete_basecase 最大补充生成次数
MAX_BASECASE_REGENERATE_COUNT = 1