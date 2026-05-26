from fastapi import APIRouter

from service.functional_test.case.api import router as case_router
from service.functional_test.requirement.api import router as requirement_router

router = APIRouter(prefix="/functional")

router.include_router(requirement_router)
router.include_router(case_router)
