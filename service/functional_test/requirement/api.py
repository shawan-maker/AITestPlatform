from fastapi import APIRouter

from service.functional_test.requirement.candidate_api import router as candidate_router
from service.functional_test.requirement.requirement_api import router as requirement_router

router = APIRouter()

router.include_router(candidate_router)
router.include_router(requirement_router)
