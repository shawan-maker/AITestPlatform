"""接口测试模块 - api

API 路由端点
"""
from fastapi import APIRouter

from service.api_test.catalog.catalog_api import router as catalog_router
from service.api_test.case.case_api import router as case_router
from service.api_test.debug.debug_api import router as debug_router
from service.api_test.dependency.dependency_api import router as dependency_router
from service.api_test.interface.interface_api import router as interface_router

router = APIRouter(prefix="/api-test", tags=["接口测试"])

router.include_router(catalog_router)
router.include_router(interface_router)
router.include_router(debug_router)
router.include_router(dependency_router)
router.include_router(case_router)
