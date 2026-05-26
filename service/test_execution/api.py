from fastapi import APIRouter

from service.test_execution.defect.defect_api import router as defect_router
from service.test_execution.manual.manual_run_api import router as manual_router
from service.test_execution.report.report_api import router as report_router
from service.test_execution.run.history_api import router as history_router
from service.test_execution.run.run_api import router as run_router

router = APIRouter(prefix="/test-execution", tags=["测试执行"])

router.include_router(run_router)
router.include_router(history_router)
router.include_router(report_router)
router.include_router(manual_router)
router.include_router(defect_router)
