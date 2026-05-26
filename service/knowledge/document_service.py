from service.core.config import MAX_UPLOAD_BYTES
from service.core.deps import get_project_or_404
from service.core.enums import IndexStatus, KnowledgeDocType
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.knowledge.file_rules import FileRules, sha256_hex
from service.knowledge.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.permissions import ensure_document_editor, ensure_document_viewer
from service.knowledge.schemas import (
    KnowledgeDocumentBrief,
    KnowledgeDocumentDetail,
    KnowledgeDocumentListQuery,
    PaginatedKnowledgeDocuments,
)
from service.knowledge.index_worker import IndexWorker
from service.knowledge.rag_gateway import RagGateway
from service.knowledge.storage import KnowledgeStorage
from service.knowledge.version_service import VersionService, version_label_from_seq
from service.knowledge.workspace_service import WorkspaceService
from service.project.models import ProjectMember, ProjectModule
from service.project.permissions import ensure_project_editor, ensure_project_viewer
from service.user.models import User


class DocumentService:
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
    async def create(
        cls,
        user: User,
        project_id: int,
        *,
        title: str,
        doc_type: KnowledgeDocType,
        parse_mode,
        module_id: int | None,
        file_name: str,
        content: bytes,
        mime_type: str | None,
    ) -> KnowledgeDocumentDetail:
        project = await get_project_or_404(project_id)
        await ensure_project_editor(project_id, user)
        if len(content) > MAX_UPLOAD_BYTES:
            raise AppException(f"文件大小超过限制 {MAX_UPLOAD_BYTES} 字节", 400)
        stripped_title = title.strip()
        if not stripped_title:
            raise AppException("文档名称不能为空", 400)
        if await KnowledgeDocument.filter(project_id=project_id, title=stripped_title).exists():
            raise AppException("同一项目内文档名称已存在", 409)
        await cls._validate_module(project_id, module_id)
        FileRules.validate_upload(
            file_name=file_name,
            content=content,
            doc_type=doc_type,
            parse_mode=parse_mode,
        )
        workspace = await WorkspaceService.ensure_workspace(project, doc_type)
        document = await KnowledgeDocument.create(
            project_id=project_id,
            module_id=module_id,
            workspace_id=workspace.id,
            doc_type=doc_type,
            parse_mode=parse_mode,
            title=stripped_title,
        )
        label = version_label_from_seq(1)
        relative_path = KnowledgeStorage.save_version_file(
            project_id=project_id,
            document_id=document.id,
            version_label=label,
            file_name=file_name,
            content=content,
        )
        version = await KnowledgeDocumentVersion.create(
            document_id=document.id,
            version_label=label,
            version_seq=1,
            file_name=file_name,
            file_path=relative_path,
            file_hash=sha256_hex(content),
            file_size=len(content),
            mime_type=mime_type,
            index_status=FileRules.initial_index_status(doc_type, parse_mode),
            created_by_id=user.id,
        )
        document.current_version_id = version.id
        await document.save(update_fields=["current_version_id"])
        if version.index_status == IndexStatus.pending:
            IndexWorker.schedule(version.id)
        return await cls.get_detail(user, document.id)

    @classmethod
    async def list_documents(
        cls,
        user: User,
        query: KnowledgeDocumentListQuery,
    ) -> PaginatedKnowledgeDocuments:
        if query.project_id is not None:
            await ensure_project_viewer(query.project_id, user)
            qs = KnowledgeDocument.filter(project_id=query.project_id)
        else:
            project_ids = await cls._accessible_project_ids(user)
            if project_ids is not None and not project_ids:
                return PaginatedKnowledgeDocuments(
                    total=0,
                    page=query.page,
                    page_size=query.page_size,
                    items=[],
                )
            qs = KnowledgeDocument.all()
            if project_ids is not None:
                qs = qs.filter(project_id__in=project_ids)

        if query.title:
            qs = qs.filter(title__icontains=query.title.strip())
        if query.project_name:
            qs = qs.filter(project__name__icontains=query.project_name.strip())
        if query.doc_type is not None:
            qs = qs.filter(doc_type=query.doc_type)
        if query.parse_mode is not None:
            qs = qs.filter(parse_mode=query.parse_mode)
        if query.index_status is not None:
            version_ids = await KnowledgeDocumentVersion.filter(
                index_status=query.index_status
            ).values_list("id", flat=True)
            qs = qs.filter(current_version_id__in=list(version_ids))

        qs = qs.order_by("-updated_at")
        total, items = await paginate(qs, query.page, query.page_size)
        briefs = [await cls._to_brief(doc) for doc in items]
        return PaginatedKnowledgeDocuments(
            total=total,
            page=query.page,
            page_size=query.page_size,
            items=briefs,
        )

    @classmethod
    async def get_detail(cls, user: User, document_id: int) -> KnowledgeDocumentDetail:
        document = await ensure_document_viewer(document_id, user)
        current = None
        if document.current_version_id:
            current_version = await KnowledgeDocumentVersion.get_or_none(
                id=document.current_version_id
            )
            if current_version:
                current = await VersionService._to_brief(current_version)
        brief = await cls._to_brief(document)
        return KnowledgeDocumentDetail(
            **brief.model_dump(),
            module_id=document.module_id,
            workspace_id=document.workspace_id,
            current_version=current,
            created_at=document.created_at,
        )

    @classmethod
    async def delete(cls, user: User, document_id: int) -> None:
        document = await ensure_document_editor(document_id, user)
        workspace = await document.workspace
        versions = await KnowledgeDocumentVersion.filter(document_id=document.id)
        for version in versions:
            if version.rag_doc_id and version.rag_backend:
                await RagGateway.delete(
                    workspace_key=workspace.workspace_key,
                    rag_doc_id=version.rag_doc_id,
                    rag_backend=version.rag_backend,
                )
            KnowledgeStorage.delete_file(version.file_path)
        await document.delete()

    @classmethod
    async def _to_brief(cls, document: KnowledgeDocument) -> KnowledgeDocumentBrief:
        project = document.project
        if not hasattr(project, "name"):
            project = await document.project
        version_label = None
        index_status = None
        updated_by_username = None
        if document.current_version_id:
            version = await KnowledgeDocumentVersion.get_or_none(id=document.current_version_id)
            if version:
                version_label = version.version_label
                index_status = version.index_status
                if version.created_by_id:
                    creator = await version.created_by
                    if creator is not None:
                        updated_by_username = creator.username
        return KnowledgeDocumentBrief(
            id=document.id,
            project_id=document.project_id,
            project_name=project.name,
            title=document.title,
            doc_type=document.doc_type,
            parse_mode=document.parse_mode,
            version_label=version_label,
            index_status=index_status,
            updated_at=document.updated_at,
            updated_by_username=updated_by_username,
        )
