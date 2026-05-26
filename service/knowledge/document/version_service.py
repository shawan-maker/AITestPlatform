from service.core.enums import IndexStatus
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.document.permissions import ensure_document_editor, ensure_document_viewer
from service.knowledge.document.schemas import KnowledgeVersionBrief, PaginatedKnowledgeVersions
from service.knowledge.document.storage import KnowledgeStorage
from service.knowledge.pipeline.index_worker import IndexWorker
from service.user.models import User

_PROCESSING_STATUSES = {IndexStatus.indexing, IndexStatus.parsing}


def version_label_from_seq(version_seq: int) -> str:
    return f"v1.{max(version_seq - 1, 0)}"


class VersionService:
    @classmethod
    async def get_version_or_404(
        cls,
        document_id: int,
        version_id: int,
    ) -> KnowledgeDocumentVersion:
        version = await KnowledgeDocumentVersion.get_or_none(
            id=version_id,
            document_id=document_id,
        )
        if version is None:
            raise AppException("文档版本不存在", 404)
        return version

    @classmethod
    async def assert_not_processing(cls, document: KnowledgeDocument) -> None:
        if await KnowledgeDocumentVersion.filter(
            document_id=document.id,
            index_status__in=_PROCESSING_STATUSES,
        ).exists():
            raise AppException("文档正在索引或解析中，请稍后再试", 409)

    @classmethod
    async def assert_version_not_processing(cls, version: KnowledgeDocumentVersion) -> None:
        if version.index_status in _PROCESSING_STATUSES:
            raise AppException("该版本正在索引或解析中，请稍后再试", 409)

    @classmethod
    async def list_versions(
        cls,
        user: User,
        document_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedKnowledgeVersions:
        await ensure_document_viewer(document_id, user)
        qs = KnowledgeDocumentVersion.filter(document_id=document_id).order_by("-version_seq")
        total, items = await paginate(qs, page, page_size)
        return PaginatedKnowledgeVersions(
            total=total,
            page=page,
            page_size=page_size,
            items=[await cls._to_brief(v) for v in items],
        )

    @classmethod
    async def resolve_download_path(
        cls,
        user: User,
        document_id: int,
        version_id: int | None = None,
    ) -> tuple[KnowledgeDocumentVersion, str]:
        await ensure_document_viewer(document_id, user)
        document = await KnowledgeDocument.get_or_none(id=document_id)
        if document is None:
            raise AppException("知识库文档不存在", 404)
        if version_id is None:
            if not document.current_version_id:
                raise AppException("文档尚无可用版本", 404)
            version = await KnowledgeDocumentVersion.get_or_none(id=document.current_version_id)
        else:
            version = await cls.get_version_or_404(document_id, version_id)
        if version is None:
            raise AppException("文档版本不存在", 404)
        if version.file_expired or not version.file_path:
            raise AppException("该版本原件已清理，无法下载", 410)
        path = KnowledgeStorage.absolute_path(version.file_path)
        if not path.is_file():
            raise AppException("文件已丢失", 404)
        return version, str(path)

    @classmethod
    async def create_new_version(
        cls,
        user: User,
        document_id: int,
        *,
        file_name: str,
        content: bytes,
        mime_type: str | None,
        file_hash: str,
    ) -> KnowledgeDocumentVersion:
        document = await ensure_document_editor(document_id, user)
        await cls.assert_not_processing(document)
        latest = (
            await KnowledgeDocumentVersion.filter(document_id=document_id)
            .order_by("-version_seq")
            .first()
        )
        next_seq = 1 if latest is None else latest.version_seq + 1
        label = version_label_from_seq(next_seq)
        relative_path = KnowledgeStorage.save_version_file(
            project_id=document.project_id,
            document_id=document.id,
            version_label=label,
            file_name=file_name,
            content=content,
        )
        version = await KnowledgeDocumentVersion.create(
            document_id=document.id,
            version_label=label,
            version_seq=next_seq,
            file_name=file_name,
            file_path=relative_path,
            file_hash=file_hash,
            file_size=len(content),
            mime_type=mime_type,
            index_status=IndexStatus.pending,
            created_by_id=user.id,
        )
        document.updated_at = version.created_at
        await document.save(update_fields=["updated_at"])
        await KnowledgeStorage.enforce_retention(document.id)
        IndexWorker.schedule(version.id)
        return version

    @classmethod
    async def trigger_reindex(cls, user: User, document_id: int) -> KnowledgeVersionBrief:
        document = await ensure_document_editor(document_id, user)
        if not document.current_version_id:
            raise AppException("文档尚无可用版本", 404)
        version = await KnowledgeDocumentVersion.get_or_none(id=document.current_version_id)
        if version is None:
            raise AppException("当前版本不存在", 404)
        await cls.assert_version_not_processing(version)
        if version.file_expired or not version.file_path:
            raise AppException("当前版本原件已清理，无法重新索引", 400)
        version.index_status = IndexStatus.pending
        version.index_error = None
        await version.save(update_fields=["index_status", "index_error"])
        IndexWorker.schedule(version.id)
        return await cls._to_brief(version)

    @classmethod
    async def _to_brief(cls, version: KnowledgeDocumentVersion) -> KnowledgeVersionBrief:
        username = None
        if version.created_by_id:
            creator = version.created_by
            if not hasattr(creator, "username"):
                creator = await version.created_by
            if creator is not None:
                username = creator.username
        return KnowledgeVersionBrief(
            id=version.id,
            document_id=version.document_id,
            version_label=version.version_label,
            version_seq=version.version_seq,
            file_name=version.file_name,
            file_size=version.file_size,
            mime_type=version.mime_type,
            index_status=version.index_status,
            index_error=version.index_error,
            file_expired=version.file_expired,
            created_by_id=version.created_by_id,
            created_by_username=username,
            created_at=version.created_at,
        )
