"""功能测试模块 - api

API 路由端点
"""
from fastapi import APIRouter

from service.functional_test.case.api import router as case_router
from service.functional_test.case.catalog_api import router as catalog_router

router = APIRouter(prefix="/functional")

router.include_router(case_router)
router.include_router(catalog_router)
