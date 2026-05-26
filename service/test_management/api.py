from fastapi import APIRouter

from service.test_management.picker.picker_api import router as picker_router
from service.test_management.suite.suite_api import router as suite_router
from service.test_management.task.task_api import router as task_router

router = APIRouter(prefix="/test-management", tags=["测试管理"])

router.include_router(suite_router)
router.include_router(task_router)
router.include_router(picker_router)
