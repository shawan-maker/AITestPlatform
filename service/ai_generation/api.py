from fastapi import APIRouter, Depends

from service.ai_generation.api_agent_api import router as api_agent_router
from service.ai_generation.functional_agent_api import router as functional_agent_router
from service.ai_generation.meta import get_agent_meta
from service.core.deps import get_current_active_user
from service.core.response import success
from service.user.models import User

router = APIRouter(prefix="/ai-generation", tags=["AI 用例生成"])

router.include_router(functional_agent_router)
router.include_router(api_agent_router)


@router.get("/meta", summary="智能体中心元数据")
async def agent_meta(user: User = Depends(get_current_active_user)):
    return success(data=get_agent_meta())
