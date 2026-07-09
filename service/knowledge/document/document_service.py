"""知识库管理模块 - document/document_service

业务逻辑服务
"""
import logging

from tortoise.expressions import Q

from service.core.settings import MAX_UPLOAD_BYTES
from service.core.deps import get_project_or_404
from service.core.enums import IndexStatus, KnowledgeDocType, RagBackend
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.document.permissions import ensure_document_editor, ensure_document_viewer
from service.knowledge.document.schemas import (
    KnowledgeDocumentBrief,
    KnowledgeDocumentDetail,
    KnowledgeDocumentListQuery,
    PaginatedKnowledgeDocuments,
    ParsedInterfaceItem,
    ParsedInterfaceListResult,
)
from service.knowledge.document.storage import KnowledgeStorage
from service.knowledge.document.parsed_interface_service import resolve_parsed_interfaces
from service.knowledge.document.save_state import compute_version_save_state
from service.knowledge.document.version_service import VersionService, version_label_from_seq
from service.knowledge.pipeline.index_worker import IndexWorker
from service.knowledge.document.workspace_service import WorkspaceService
from service.knowledge.pipeline.index_worker import IndexWorker
from service.knowledge.pipeline.rag_gateway import RagGateway
from service.knowledge.rules.file_rules import FileRules, sha256_hex
from service.project.models import ProjectMember, ProjectModule
from service.project.permissions import ensure_project_editor, ensure_project_viewer
from service.user.models import User

logger = logging.getLogger(__name__)


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
            await IndexWorker.start_processing(
                version.id,
                doc_type=doc_type,
                parse_mode=parse_mode,
                content=content,
            )
        # 从 DB 重新读取 version 状态，确认 start_processing 是否已经改了它
        refreshed = await KnowledgeDocumentVersion.get_or_none(id=version.id)
        return await cls.get_detail(user, document.id)

    @classmethod
    async def list_documents(
        cls,
        user: User,
        query: KnowledgeDocumentListQuery,
    ) -> PaginatedKnowledgeDocuments:
        await IndexWorker.detect_and_fail_timeouts()
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
        parsed_interfaces: list[ParsedInterfaceItem] = []
        if (
            document.doc_type == KnowledgeDocType.api_doc
            and document.current_version_id
        ):
            current_version = await KnowledgeDocumentVersion.get_or_none(
                id=document.current_version_id
            )
            if current_version:
                parsed_interfaces = await resolve_parsed_interfaces(
                    document, current_version
                )
        return KnowledgeDocumentDetail(
            **brief.model_dump(),
            workspace_id=document.workspace_id,
            current_version=current,
            created_at=document.created_at,
            parsed_interfaces=parsed_interfaces,
        )

    @classmethod
    async def delete(cls, user: User, document_id: int) -> None:
        document = await ensure_document_editor(document_id, user)
        await VersionService.assert_not_processing(document)
        workspace = await document.workspace
        versions = await KnowledgeDocumentVersion.filter(document_id=document.id)
        for version in versions:
            if version.rag_doc_id and version.rag_backend:
                # 正常路径：有 doc_id，直接删
                await RagGateway.delete(
                    workspace_key=workspace.workspace_key,
                    rag_doc_id=version.rag_doc_id,
                    rag_backend=version.rag_backend,
                )
            else:
                # 兜底：历史数据 rag_doc_id 可能为空（旧版索引失败未保存），
                # 用约定的 doc_id 格式尝试清理 LightRAG 残留
                fallback_doc_id = f"knowledge/{document.id}/{version.id}"
                try:
                    await RagGateway.delete(
                        workspace_key=workspace.workspace_key,
                        rag_doc_id=fallback_doc_id,
                        rag_backend=RagBackend.rag_client,
                    )
                except Exception:
                    pass
            KnowledgeStorage.delete_file(version.file_path)
        await document.delete()

    @classmethod
    async def batch_delete(cls, user: User, data) -> dict:
        deleted_ids = []
        failures = []
        for item_id in data.document_ids:
            try:
                await cls.delete(user, item_id)
                deleted_ids.append(item_id)
            except AppException as e:
                failures.append({'document_id': item_id, 'message': e.message})
            except Exception as e:
                failures.append({'document_id': item_id, 'message': str(e)})
        return {'deleted_ids': deleted_ids, 'failures': failures}

    @classmethod
    async def get_version_text_preview(
        cls,
        user: User,
        document_id: int,
        version_id: int | None = None,
    ) -> dict:
        document = await ensure_document_viewer(document_id, user)
        vid = version_id or document.current_version_id
        if not vid:
            raise AppException("文档尚无可用版本", 404)
        version = await KnowledgeDocumentVersion.get_or_none(
            id=vid, document_id=document_id
        )
        if version is None:
            raise AppException("文档版本不存在", 404)
        if version.file_expired or not version.file_path:
            raise AppException("该版本原件已清理，无法读取全文", 410)
        path = KnowledgeStorage.absolute_path(version.file_path)
        if not path.is_file():
            raise AppException("文件已丢失", 404)
        text = path.read_text(encoding="utf-8", errors="ignore")
        # 简单的预览逻辑：截取前1000个字符
        preview = text[:1000] if len(text) > 1000 else None
        stripped = text.strip()
        truncated = preview is not None and len(stripped) > len(preview or "")
        return {
            "text": text,
            "truncated": truncated,
            "version_label": version.version_label,
            "document_title": document.title,
            "suggested_title": document.title,  # 使用文档标题作为建议标题
        }

    @classmethod
    async def get_version_parsed_interfaces(
        cls,
        user: User,
        document_id: int,
        version_id: int,
    ) -> ParsedInterfaceListResult:
        document = await ensure_document_viewer(document_id, user)
        if document.doc_type != KnowledgeDocType.api_doc:
            raise AppException("仅接口文档支持查看解析接口", 400)
        version = await KnowledgeDocumentVersion.get_or_none(
            id=version_id, document_id=document_id
        )
        if version is None:
            raise AppException("文档版本不存在", 404)
        items = await resolve_parsed_interfaces(document, version)
        return ParsedInterfaceListResult(
            document_id=document_id,
            version_id=version_id,
            items=items,
        )

    @classmethod
    async def _to_brief(cls, document: KnowledgeDocument) -> KnowledgeDocumentBrief:
        project = document.project
        if not hasattr(project, "name"):
            project = await document.project
        module_name = None
        if document.module_id:
            module = document.module
            if not hasattr(module, "name"):
                module = await document.module
            if module is not None:
                module_name = module.name
        version_label = None
        index_status = None
        parse_status = None
        interfaces_saved = False
        can_save_interfaces = False
        updated_by_username = None

        # 确定用于展示的版本：优先取"最新处理中版本"，否则取 current_version
        display_version = None
        if document.current_version_id:
            display_version = await KnowledgeDocumentVersion.get_or_none(
                id=document.current_version_id
            )

        # 检查是否存在比当前版本更新且仍在处理中的版本（重传/更新场景）
        # 覆盖所有中间状态：
        #   - index_status: pending / indexing / parsing（Swagger/OpenAPI 同步解析、RAG索引中）
        #   - parse_status: parsing（RAG已完成但AI结构化解析仍在进行）
        if display_version:
            processing_version = await KnowledgeDocumentVersion.filter(
                document_id=document.id,
                version_seq__gt=display_version.version_seq,
            ).filter(
                Q(index_status__in=["pending", "indexing", "parsing"])
                | Q(parse_status="parsing")
            ).order_by("-version_seq").first()
            if processing_version:
                display_version = processing_version

        if display_version:
            version_label = display_version.version_label
            index_status = display_version.index_status
            parse_status = display_version.parse_status
            save_state = await compute_version_save_state(document, display_version)
            interfaces_saved = save_state.interfaces_saved
            can_save_interfaces = save_state.can_save_interfaces
            if display_version.created_by_id:
                creator = await display_version.created_by
                if creator is not None:
                    updated_by_username = creator.username
        return KnowledgeDocumentBrief(
            id=document.id,
            project_id=document.project_id,
            project_name=project.name,
            module_id=document.module_id,
            module_name=module_name,
            title=document.title,
            doc_type=document.doc_type,
            parse_mode=document.parse_mode,
            version_label=version_label,
            current_version_id=document.current_version_id,
            index_status=index_status,
            parse_status=parse_status,
            interfaces_saved=interfaces_saved,
            can_save_interfaces=can_save_interfaces,
            updated_at=document.updated_at,
            updated_by_username=updated_by_username,
        )
