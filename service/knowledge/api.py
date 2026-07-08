"""知识库管理模块 - api

API 路由端点
"""
from fastapi import APIRouter

from service.knowledge.document.document_api import router as document_router
from service.knowledge.downstream.import_api import router as import_router

router = APIRouter(prefix="/knowledge", tags=["知识库"])

router.include_router(document_router)
router.include_router(import_router)
