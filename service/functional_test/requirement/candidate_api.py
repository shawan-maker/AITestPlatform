from fastapi import APIRouter, Depends, Query

from service.core.deps import get_current_active_user
from service.core.response import success
from service.functional_test.requirement.candidate_service import CandidateService
from service.functional_test.requirement.schemas import CandidateConfirmRequest, CandidateListQuery, CandidateUpdateRequest
from service.user.models import User

router = APIRouter(tags=["功能测试-需求候选"])


def get_candidate_list_query(
    project_id: int | None = Query(None, ge=1),
    title: str | None = Query(None),
    module_id: int | None = Query(None, ge=1),
    created_by: int | None = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CandidateListQuery:
    return CandidateListQuery(
        project_id=project_id,
        title=title,
        module_id=module_id,
        created_by=created_by,
        page=page,
        page_size=page_size,
    )


@router.get("/requirements/candidates", summary="待确认需求候选列表")
async def list_candidates(
    query: CandidateListQuery = Depends(get_candidate_list_query),
    user: User = Depends(get_current_active_user),
):
    data = await CandidateService.list_candidates(user, query)
    return success(data=data)


@router.get("/requirements/candidates/count", summary="待确认候选数量")
async def count_candidates(
    project_id: int | None = Query(None, ge=1),
    user: User = Depends(get_current_active_user),
):
    count = await CandidateService.count_candidates(user, project_id)
    return success(data={"count": count})


@router.get("/requirements/candidates/{candidate_id}", summary="候选详情")
async def get_candidate(
    candidate_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await CandidateService.get_detail(user, candidate_id)
    return success(data=data)


@router.post("/requirements/candidates/{candidate_id}/confirm", summary="确认候选为正式需求")
async def confirm_candidate(
    candidate_id: int,
    body: CandidateConfirmRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CandidateService.confirm(user, candidate_id, body)
    return success(data=data, message="需求确认成功")


@router.patch("/requirements/candidates/{candidate_id}", summary="编辑候选需求")
async def update_candidate(
    candidate_id: int,
    body: CandidateUpdateRequest,
    user: User = Depends(get_current_active_user),
):
    data = await CandidateService.update(user, candidate_id, body)
    return success(data=data, message="需求编辑成功")


@router.delete("/requirements/candidates/{candidate_id}", summary="取消候选")
async def cancel_candidate(
    candidate_id: int,
    user: User = Depends(get_current_active_user),
):
    await CandidateService.cancel(user, candidate_id)
    return success(message="候选已取消")
