from fastapi import APIRouter

from service.functional_test.case.case_api import router as case_router
from service.functional_test.case.catalog_api import router as catalog_router
from service.functional_test.case.generation_api import router as generation_router

router = APIRouter()

router.include_router(catalog_router)
router.include_router(case_router)
router.include_router(generation_router)
