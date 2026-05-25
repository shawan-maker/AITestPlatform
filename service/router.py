from fastapi import APIRouter

from service.ai_generation.api import router as ai_generation_router
from service.api_test.api import router as api_test_router
from service.functional_test.api import router as functional_test_router
from service.knowledge.api import router as knowledge_router
from service.project.api import router as project_router
from service.test_environment.api import router as test_environment_router
from service.test_execution.api import router as test_execution_router
from service.test_management.api import router as test_management_router
from service.user.auth_api import router as auth_router
from service.user.users_api import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(project_router)
api_router.include_router(test_environment_router)
api_router.include_router(knowledge_router)
api_router.include_router(functional_test_router)
api_router.include_router(api_test_router)
api_router.include_router(test_management_router)
api_router.include_router(test_execution_router)
api_router.include_router(ai_generation_router)
