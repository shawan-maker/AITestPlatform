from datetime import datetime, timezone

from service.core.enums import IndexStatus
from service.functional_test.models import RequirementCandidate
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.document.storage import KnowledgeStorage

_PREVIEW_LEN = 8000


def _text_preview(version: KnowledgeDocumentVersion) -> str | None:
    if version.file_expired or not version.file_path:
        return None
    path = KnowledgeStorage.absolute_path(version.file_path)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        preview = text[:_PREVIEW_LEN].strip()
        return preview or None
    except OSError:
        return None


async def sync_requirement_candidate(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
) -> RequirementCandidate:
    title = f"{document.title} ({version.version_label})"
    description = _text_preview(version)
    now = datetime.now(timezone.utc)

    existing = await RequirementCandidate.get_or_none(
        source_document_id=document.id,
        source_document_version_id=version.id,
    )
    if existing is not None:
        existing.title = title
        existing.description = description
        existing.source_version_label = version.version_label
        existing.index_status = IndexStatus.indexed
        existing.indexed_at = now
        await existing.save(
            update_fields=[
                "title",
                "description",
                "source_version_label",
                "index_status",
                "indexed_at",
            ]
        )
        return existing

    return await RequirementCandidate.create(
        project_id=document.project_id,
        module_id=document.module_id,
        title=title,
        description=description,
        source_document_id=document.id,
        source_document_version_id=version.id,
        source_version_label=version.version_label,
        index_status=IndexStatus.indexed,
        indexed_at=now,
        created_by_id=version.created_by_id,
    )
