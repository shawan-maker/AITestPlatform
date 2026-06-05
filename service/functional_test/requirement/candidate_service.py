import re

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
    CandidateUpdateRequest,
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
        await cand.fetch_related("project", "module", "created_by")
        return CandidateBrief(
            id=cand.id,
            project_id=cand.project_id,
            project_name=cand.project.name,
            module_id=cand.module_id,
            module_name=cand.module.name if cand.module else None,
            title=cand.title,
            source_type=RequirementSourceType.knowledge,
            source_document_id=cand.source_document_id,
            source_document_version_id=cand.source_document_version_id,
            source_version_label=cand.source_version_label,
            index_status=cand.index_status,
            indexed_at=cand.indexed_at,
            created_by_username=cand.created_by.username if cand.created_by else None,
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
        if query.created_by is not None:
            qs = qs.filter(created_by_id=query.created_by)

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
    async def _resolve_confirm_title(
        cls,
        project_id: int,
        cand: RequirementCandidate,
        data: CandidateConfirmRequest,
    ) -> str:
        from service.knowledge.document.models import KnowledgeDocument

        document = await KnowledgeDocument.get_or_none(id=cand.source_document_id)
        default_title = document.title if document else cand.title
        title = (data.title or default_title).strip()
        if not title:
            raise AppException("需求标题不能为空", 400)
        if await RequirementDoc.filter(project_id=project_id, title=title).exists():
            if data.direct_save:
                title = await cls._unique_title(project_id, title)
            else:
                raise AppException("同一项目内需求标题已存在", 409)
        return title

    @staticmethod
    async def _unique_title(project_id: int, base: str) -> str:
        stem = re.sub(r"_copy\d*$", "", base)
        candidate = f"{stem}_copy"
        suffix = 2
        while await RequirementDoc.filter(project_id=project_id, title=candidate).exists():
            candidate = f"{stem}_copy{suffix}"
            suffix += 1
        return candidate

    @classmethod
    async def get_for_document_version(
        cls,
        user: User,
        document_id: int,
        version_id: int | None = None,
    ) -> CandidateDetail | None:
        from service.knowledge.document.models import KnowledgeDocument
        from service.knowledge.document.permissions import ensure_document_viewer

        document = await ensure_document_viewer(document_id, user)
        vid = version_id or document.current_version_id
        if not vid:
            return None
        cand = await RequirementCandidate.get_or_none(
            source_document_id=document_id,
            source_document_version_id=vid,
        )
        if cand is None:
            return None
        existing = await RequirementDoc.get_or_none(
            source_document_id=document_id,
            source_document_version_id=vid,
        )
        if existing is not None:
            return None
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

        title = await cls._resolve_confirm_title(cand.project_id, cand, data)

        async with in_transaction():
            doc = await RequirementDoc.create(
                project_id=cand.project_id,
                module_id=module_id,
                title=title,
                doc_no=None,
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
                updated_by_id=user.id,
            )
            await cand.delete()

        from service.functional_test.requirement.requirement_service import RequirementService

        return await RequirementService._to_detail(doc)

    @classmethod
    async def cancel(cls, user: User, candidate_id: int) -> None:
        cand = await cls._get_or_404(candidate_id)
        await ensure_requirement_editor(cand.project_id, user)
        await cand.delete()

    @classmethod
    async def update(
        cls,
        user: User,
        candidate_id: int,
        data: CandidateUpdateRequest,
    ) -> CandidateDetail:
        cand = await cls._get_or_404(candidate_id)
        await ensure_requirement_editor(cand.project_id, user)
        if data.module_id is not None:
            await cls._validate_module(cand.project_id, data.module_id)
            cand.module_id = data.module_id
        if data.title is not None:
            title = data.title.strip()
            if not title:
                raise AppException("需求标题不能为空", 400)
            cand.title = title
        if data.description is not None:
            cand.description = data.description
        await cand.save()
        return await cls._to_detail(cand)
