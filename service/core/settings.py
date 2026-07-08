import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# 部署配置（服务器部署 / Nginx 反向代理）
# ---------------------------------------------------------------------------
BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
# CORS 允许的前端域名，逗号分隔。生产环境设为实际域名，同域部署可留空
CORS_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]
# 日志文件路径，留空则不写文件日志
LOG_FILE: str = os.getenv("LOG_FILE", "")

# ---------------------------------------------------------------------------
# 数据库与认证
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql://root:123456@127.0.0.1:3306/aiTestPlatform",
)
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
REDIS_URL: str | None = os.getenv("REDIS_URL")

# ---------------------------------------------------------------------------
# 应用常量
# ---------------------------------------------------------------------------
API_V1_PREFIX: str = "/api/v1"
APP_TITLE: str = "AI Test Platform"
APP_VERSION: str = "0.1.0"
MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
KNOWLEDGE_UPLOAD_ROOT: Path = BASE_DIR / "data" / "rag" / "document"
KNOWLEDGE_PARSE_ROOT: Path = BASE_DIR / "data" / "rag" / "parsed"
MAX_COMPLETE_TEST_POINTS: int = int(os.getenv("MAX_COMPLETE_TEST_POINTS", "1"))

# ---------------------------------------------------------------------------
# RAG 知识库配置
# ---------------------------------------------------------------------------
RAG_SERVER_URL: str | None = os.getenv("RAG_SERVER_URL")
RAG_API_KEY: str | None = os.getenv("RAG_API_KEY")
# RAG 存储与文档路径
OUTPUT_DIR: str = os.path.join(BASE_DIR, "data", "rag", "output")
RAG_MANAGE_STORAGE: str = os.path.join(BASE_DIR, "data", "rag", "rag_storage")
DOCUMENT_DIR: str = os.path.join(BASE_DIR, "data", "rag", "document")

# ---------------------------------------------------------------------------
# AI 生成配置
# ---------------------------------------------------------------------------
AI_GENERATION_DEFAULT_NOTICE: str = os.getenv(
    "AI_GENERATION_DEFAULT_NOTICE",
    "对于不能重复使用的数据，请使用工具随机生成数据",
)
AI_AGENT_SESSION_HISTORY_LIMIT: int = int(
    os.getenv("AI_AGENT_SESSION_HISTORY_LIMIT", "10")
)

# Agent 提示词中的示例占位（非真实环境，可通过 .env 覆盖）
AI_AGENT_PROMPT_EXAMPLE_BASE_URL: str = os.getenv(
    "AI_AGENT_PROMPT_EXAMPLE_BASE_URL", "http://example.test"
)
AI_AGENT_PROMPT_EXAMPLE_DB_HOST: str = os.getenv(
    "AI_AGENT_PROMPT_EXAMPLE_DB_HOST", "db.example.test"
)
AI_AGENT_PROMPT_EXAMPLE_DB_USER: str = os.getenv(
    "AI_AGENT_PROMPT_EXAMPLE_DB_USER", "demo_user"
)
AI_AGENT_PROMPT_EXAMPLE_DB_PASSWORD: str = os.getenv(
    "AI_AGENT_PROMPT_EXAMPLE_DB_PASSWORD", "***"
)
AI_AGENT_PROMPT_EXAMPLE_PROJECT: str = os.getenv(
    "AI_AGENT_PROMPT_EXAMPLE_PROJECT", "示例项目"
)
AI_AGENT_PROMPT_EXAMPLE_MODULE: str = os.getenv(
    "AI_AGENT_PROMPT_EXAMPLE_MODULE", "示例模块"
)
AI_AGENT_PROMPT_EXAMPLE_USERNAME: str = os.getenv(
    "AI_AGENT_PROMPT_EXAMPLE_USERNAME", "demo_user"
)
AI_AGENT_PROMPT_EXAMPLE_PASSWORD: str = os.getenv(
    "AI_AGENT_PROMPT_EXAMPLE_PASSWORD", "demo_password"
)

# 本地 demo 脚本路径（仅 workflow __main__ / 开发 fallback 使用，生产路径应走 DB 环境）
AI_DEMO_GLOBAL_FUNC_PATH: Path = Path(
    os.getenv(
        "AI_DEMO_GLOBAL_FUNC_PATH",
        str(BASE_DIR / "data" / "test_data" / "Tools.py"),
    )
)
AI_DEMO_FILES_DIR: Path = Path(
    os.getenv("AI_DEMO_FILES_DIR", str(BASE_DIR / "data" / "test_files"))
)

# workflow __main__ 本地演示开关（生产路径不应依赖）
AITESTPLATFORM_ALLOW_WORKFLOW_MAIN: bool = (
    os.getenv("AITESTPLATFORM_ALLOW_WORKFLOW_MAIN", "").strip() == "1"
)

# ---------------------------------------------------------------------------
# AI 工作流配置
# ---------------------------------------------------------------------------
# 配置生成可执行接口用例的最大重试次数
MAX_GENERATOR_COUNT: int = 3
# 配置预执行的批次大小（并发 HTTP 请求数，结构化阶段不限制）
MAX_BATCH_SIZE: int = 5
# 基础用例覆盖率不足时，complete_basecase 最大补充生成次数
MAX_BASECASE_REGENERATE_COUNT: int = 1

# ---------------------------------------------------------------------------
# LLM 大模型实例（全局共享，request_timeout 防止永久阻塞）
# ---------------------------------------------------------------------------
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "gpt-4o"),
    api_key=os.getenv("LLM_BINDING_API_KEY"),
    base_url=os.getenv("LLM_BINDING_HOST"),
    request_timeout=int(os.getenv("LLM_REQUEST_TIMEOUT", "120")),
    max_tokens=int(os.getenv("LLM_MAX_TOKENS", "16384")),
    max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
)

# ---------------------------------------------------------------------------
# ORM 配置（Tortoise + Aerich）
# ---------------------------------------------------------------------------
TORTOISE_ORM = {
    "connections": {"default": DATABASE_URL},
    "apps": {
        "models": {
            "models": [
                "aerich.models",
                "service.user.models",
                "service.project.models",
                "service.test_environment.models",
                "service.knowledge.models",
                "service.functional_test.models",
                "service.api_test.models",
                "service.test_management.models",
                "service.test_execution.models",
                "service.ai_generation.models",
            ],
            "default_connection": "default",
        }
    },
}
