from tortoise.transactions import in_transaction

from service.core.enums import IndexStatus, RequirementSourceType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.functional_test.requirement.models import RequirementCandidate, RequirementDoc
from service.functional_test.permissions import (
    ensure_requirement_editor,
    ensure_requirement_viewer,
)
from service.functional_test.requirement.schemas import (
    CandidateBrief,
    CandidateConfirmRequest,
    CandidateDetail,
    CandidateListQuery,
    PaginatedCandidates,
    RequirementDetail,
)
from service.project.models import Project, ProjectMember, ProjectModule
from service.user.models import User


class CandidateService:
    @classmethod
    async def _accessible_project_ids(cls, user: User) -> list[int] | None:
        if user.is_super_admin:
            return None
        return list(
            await ProjectMember.filter(user_id=user.id).values_list("project_id", flat=True)
        )

    @classmethod
    async def _get_or_404(cls, candidate_id: int) -> RequirementCandidate:
        cand = await RequirementCandidate.get_or_none(id=candidate_id)
        if cand is None:
            raise AppException("需求候选不存在", 404)
        return cand

    @classmethod
    async def _validate_module(cls, project_id: int, module_id: int | None) -> None:
        if module_id is None:
            return
        exists = await ProjectModule.filter(id=module_id, project_id=project_id).exists()
        if not exists:
            raise AppException("项目模块不存在", 404)

    @classmethod
    async def _to_brief(cls, cand: RequirementCandidate) -> CandidateBrief:
        await cand.fetch_related("project", "module")
        return CandidateBrief(
            id=cand.id,
            project_id=cand.project_id,
            project_name=cand.project.name,
            module_id=cand.module_id,
            module_name=cand.module.name if cand.module else None,
            title=cand.title,
            source_document_id=cand.source_document_id,
            source_document_version_id=cand.source_document_version_id,
            source_version_label=cand.source_version_label,
            index_status=cand.index_status,
            indexed_at=cand.indexed_at,
            created_at=cand.created_at,
        )

    @classmethod
    async def _to_detail(cls, cand: RequirementCandidate) -> CandidateDetail:
        await cand.fetch_related("created_by")
        brief = await cls._to_brief(cand)
        return CandidateDetail(
            **brief.model_dump(),
            description=cand.description,
            created_by_username=cand.created_by.username if cand.created_by else None,
        )

    @classmethod
    async def list_candidates(
        cls,
        user: User,
        query: CandidateListQuery,
    ) -> PaginatedCandidates:
        if query.project_id is not None:
            await ensure_requirement_viewer(query.project_id, user)
            qs = RequirementCandidate.filter(project_id=query.project_id)
        else:
            project_ids = await cls._accessible_project_ids(user)
            if project_ids is not None and not project_ids:
                return PaginatedCandidates(total=0, page=query.page, page_size=query.page_size, items=[])
            qs = RequirementCandidate.all()
            if project_ids is not None:
                qs = qs.filter(project_id__in=project_ids)

        if query.title:
            qs = qs.filter(title__icontains=query.title.strip())
        if query.module_id is not None:
            qs = qs.filter(module_id=query.module_id)

        qs = qs.order_by("-created_at")
        total, rows = await paginate(qs, query.page, query.page_size)
        items = [await cls._to_brief(row) for row in rows]
        return PaginatedCandidates(
            total=total, page=query.page, page_size=query.page_size, items=items
        )

    @classmethod
    async def count_candidates(cls, user: User, project_id: int | None) -> int:
        if project_id is not None:
            await ensure_requirement_viewer(project_id, user)
            qs = RequirementCandidate.filter(project_id=project_id)
        else:
            project_ids = await cls._accessible_project_ids(user)
            if project_ids is not None and not project_ids:
                return 0
            qs = RequirementCandidate.all()
            if project_ids is not None:
                qs = qs.filter(project_id__in=project_ids)
        return await qs.count()

    @classmethod
    async def get_detail(cls, user: User, candidate_id: int) -> CandidateDetail:
        cand = await cls._get_or_404(candidate_id)
        await ensure_requirement_viewer(cand.project_id, user)
        return await cls._to_detail(cand)

    @classmethod
    async def confirm(
        cls,
        user: User,
        candidate_id: int,
        data: CandidateConfirmRequest,
    ) -> RequirementDetail:
        cand = await cls._get_or_404(candidate_id)
        await ensure_requirement_editor(cand.project_id, user)

        existing_doc = await RequirementDoc.get_or_none(
            source_document_id=cand.source_document_id,
            source_document_version_id=cand.source_document_version_id,
        )
        if existing_doc is not None:
            raise AppException("该版本已确认", 409)

        module_id = data.module_id if data.module_id is not None else cand.module_id
        await cls._validate_module(cand.project_id, module_id)

        title = (data.title or cand.title).strip()
        if not title:
            raise AppException("需求标题不能为空", 400)
        if await RequirementDoc.filter(project_id=cand.project_id, title=title).exists():
            raise AppException("同一项目内需求标题已存在", 409)

        async with in_transaction():
            doc = await RequirementDoc.create(
                project_id=cand.project_id,
                module_id=module_id,
                title=title,
                description=data.description if data.description is not None else cand.description,
                priority=data.priority,
                status=data.status,
                source_type=RequirementSourceType.knowledge,
                source_document_id=cand.source_document_id,
                source_document_version_id=cand.source_document_version_id,
                source_version_label=cand.source_version_label,
                index_status=cand.index_status or IndexStatus.indexed,
                indexed_at=cand.indexed_at,
                created_by_id=user.id,
            )
            await cand.delete()

        from service.functional_test.requirement.requirement_service import RequirementService

        return await RequirementService._to_detail(doc)

    @classmethod
    async def cancel(cls, user: User, candidate_id: int) -> None:
        cand = await cls._get_or_404(candidate_id)
        await ensure_requirement_editor(cand.project_id, user)
        await cand.delete()
