from fastapi import APIRouter

from service.test_environment.database.api import bind_router as db_bind_router
from service.test_environment.database.api import router as database_router
from service.test_environment.file.api import router as file_router
from service.test_environment.function.api import bind_router as function_bind_router
from service.test_environment.function.api import router as function_router
from service.test_environment.variable.api import router as variable_router

router = APIRouter(prefix="/env")

router.include_router(variable_router)
router.include_router(database_router)
router.include_router(db_bind_router)
router.include_router(function_router)
router.include_router(function_bind_router)
router.include_router(file_router)
