from service.core.deps import get_project_or_404
from service.core.enums import IndexStatus, RequirementSourceType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.functional_test.case.models import FunctionalCase
from service.functional_test.requirement.models import RequirementDoc
from service.functional_test.permissions import (
    ensure_requirement_editor,
    ensure_requirement_viewer,
)
from service.functional_test.requirement.schemas import (
    PaginatedRequirements,
    RequirementBrief,
    RequirementCreateRequest,
    RequirementDeleteResult,
    RequirementDetail,
    RequirementListQuery,
    RequirementUpdateRequest,
)
from service.project.models import Project, ProjectMember, ProjectModule
from service.user.models import User


class RequirementService:
    @classmethod
    async def _accessible_project_ids(cls, user: User) -> list[int] | None:
        if user.is_super_admin:
            return None
        return list(
            await ProjectMember.filter(user_id=user.id).values_list("project_id", flat=True)
        )

    @classmethod
    async def _validate_module(cls, project_id: int, module_id: int | None) -> None:
        if module_id is None:
            return
        exists = await ProjectModule.filter(id=module_id, project_id=project_id).exists()
        if not exists:
            raise AppException("项目模块不存在", 404)

    @classmethod
    async def _ensure_title_unique(
        cls,
        project_id: int,
        title: str,
        *,
        exclude_id: int | None = None,
    ) -> None:
        qs = RequirementDoc.filter(project_id=project_id, title=title)
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if await qs.exists():
            raise AppException("同一项目内需求标题已存在", 409)

    @classmethod
    async def _get_or_404(cls, requirement_id: int) -> RequirementDoc:
        doc = await RequirementDoc.get_or_none(id=requirement_id)
        if doc is None:
            raise AppException("需求不存在", 404)
        return doc

    @classmethod
    async def _to_brief(cls, doc: RequirementDoc) -> RequirementBrief:
        await doc.fetch_related("project", "module", "created_by")
        return RequirementBrief(
            id=doc.id,
            project_id=doc.project_id,
            project_name=doc.project.name,
            module_id=doc.module_id,
            module_name=doc.module.name if doc.module else None,
            title=doc.title,
            source_type=doc.source_type,
            priority=doc.priority,
            status=doc.status,
            created_by_username=doc.created_by.username if doc.created_by else None,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    @classmethod
    async def _to_detail(cls, doc: RequirementDoc) -> RequirementDetail:
        brief = await cls._to_brief(doc)
        linked_case_count = await FunctionalCase.filter(requirement_id=doc.id).count()
        return RequirementDetail(
            **brief.model_dump(),
            doc_no=doc.doc_no,
            description=doc.description,
            source_document_id=doc.source_document_id,
            source_document_version_id=doc.source_document_version_id,
            source_version_label=doc.source_version_label,
            index_status=doc.index_status,
            indexed_at=doc.indexed_at,
            linked_case_count=linked_case_count,
        )

    @classmethod
    async def list_requirements(
        cls,
        user: User,
        query: RequirementListQuery,
    ) -> PaginatedRequirements:
        if query.project_id is not None:
            await ensure_requirement_viewer(query.project_id, user)
            qs = RequirementDoc.filter(project_id=query.project_id)
        else:
            project_ids = await cls._accessible_project_ids(user)
            if project_ids is not None and not project_ids:
                return PaginatedRequirements(total=0, page=query.page, page_size=query.page_size, items=[])
            qs = RequirementDoc.all()
            if project_ids is not None:
                qs = qs.filter(project_id__in=project_ids)

        if query.title:
            qs = qs.filter(title__icontains=query.title.strip())
        if query.project_name:
            project_ids = await Project.filter(name__icontains=query.project_name.strip()).values_list(
                "id", flat=True
            )
            qs = qs.filter(project_id__in=list(project_ids))
        if query.source_type is not None:
            qs = qs.filter(source_type=query.source_type)
        if query.module_id is not None:
            qs = qs.filter(module_id=query.module_id)

        qs = qs.order_by("-updated_at")
        total, rows = await paginate(qs, query.page, query.page_size)
        items = [await cls._to_brief(row) for row in rows]
        return PaginatedRequirements(
            total=total, page=query.page, page_size=query.page_size, items=items
        )

    @classmethod
    async def get_detail(cls, user: User, requirement_id: int) -> RequirementDetail:
        doc = await cls._get_or_404(requirement_id)
        await ensure_requirement_viewer(doc.project_id, user)
        return await cls._to_detail(doc)

    @classmethod
    async def create(cls, user: User, data: RequirementCreateRequest) -> RequirementDetail:
        await get_project_or_404(data.project_id)
        await ensure_requirement_editor(data.project_id, user)
        await cls._validate_module(data.project_id, data.module_id)
        title = data.title.strip()
        if not title:
            raise AppException("需求标题不能为空", 400)
        await cls._ensure_title_unique(data.project_id, title)
        doc = await RequirementDoc.create(
            project_id=data.project_id,
            module_id=data.module_id,
            title=title,
            doc_no=data.doc_no,
            description=data.description,
            priority=data.priority,
            status=data.status,
            source_type=RequirementSourceType.manual,
            index_status=IndexStatus.na,
            created_by_id=user.id,
        )
        return await cls._to_detail(doc)

    @classmethod
    async def update(
        cls,
        user: User,
        requirement_id: int,
        data: RequirementUpdateRequest,
    ) -> RequirementDetail:
        doc = await cls._get_or_404(requirement_id)
        await ensure_requirement_editor(doc.project_id, user)
        if data.module_id is not None:
            await cls._validate_module(doc.project_id, data.module_id)
            doc.module_id = data.module_id
        if data.title is not None:
            title = data.title.strip()
            if not title:
                raise AppException("需求标题不能为空", 400)
            await cls._ensure_title_unique(doc.project_id, title, exclude_id=doc.id)
            doc.title = title
        if data.doc_no is not None:
            doc.doc_no = data.doc_no
        if data.description is not None:
            doc.description = data.description
        if data.priority is not None:
            doc.priority = data.priority
        if data.status is not None:
            doc.status = data.status
        await doc.save()
        return await cls._to_detail(doc)

    @classmethod
    async def delete(cls, user: User, requirement_id: int) -> RequirementDeleteResult:
        doc = await cls._get_or_404(requirement_id)
        await ensure_requirement_editor(doc.project_id, user)
        linked_case_count = await FunctionalCase.filter(requirement_id=doc.id).count()
        await doc.delete()
        return RequirementDeleteResult(linked_case_count=linked_case_count)
