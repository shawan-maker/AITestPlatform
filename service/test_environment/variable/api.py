"""测试环境管理模块 - variable/api

API 路由端点
"""
from fastapi import APIRouter, Depends

from service.test_environment.variable.catalog_api import router as catalog_router
from service.test_environment.variable.environment_api import router as environment_router
from service.test_environment.variable.global_config_api import router as global_config_router
from service.test_environment.variable.import_export_api import router as import_export_router
from service.test_environment.variable.snapshot_api import router as snapshot_router

router = APIRouter()

router.include_router(catalog_router)
router.include_router(environment_router)
router.include_router(global_config_router)
router.include_router(snapshot_router)
router.include_router(import_export_router)
