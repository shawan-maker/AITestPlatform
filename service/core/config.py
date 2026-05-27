import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql://root:123456@127.0.0.1:3306/aiTestPlatform",
)
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
REDIS_URL: str | None = os.getenv("REDIS_URL")
API_V1_PREFIX: str = "/api/v1"
APP_TITLE: str = "AI Test Platform"
APP_VERSION: str = "0.1.0"
MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
KNOWLEDGE_UPLOAD_ROOT: Path = BASE_DIR / "rag" / "document"
KNOWLEDGE_PARSE_ROOT: Path = BASE_DIR / "rag" / "parsed"
MAX_COMPLETE_TEST_POINTS: int = int(os.getenv("MAX_COMPLETE_TEST_POINTS", "1"))
AI_GENERATION_DEFAULT_NOTICE: str = os.getenv(
    "AI_GENERATION_DEFAULT_NOTICE",
    "对于不能重复使用的数据，请使用工具随机生成数据",
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
        str(BASE_DIR / "test_data" / "Tools.py"),
    )
)
AI_DEMO_FILES_DIR: Path = Path(
    os.getenv("AI_DEMO_FILES_DIR", str(BASE_DIR / "test_data" / "files"))
)

# workflow __main__ 本地演示开关（生产路径不应依赖）
AITESTPLATFORM_ALLOW_WORKFLOW_MAIN: bool = (
    os.getenv("AITESTPLATFORM_ALLOW_WORKFLOW_MAIN", "").strip() == "1"
)

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
