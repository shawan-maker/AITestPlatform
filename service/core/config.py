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
