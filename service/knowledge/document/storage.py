"""知识库管理模块 - document/storage

storage
"""
from pathlib import Path

from service.core.settings import BASE_DIR, KNOWLEDGE_UPLOAD_ROOT
from service.knowledge.document.models import KnowledgeDocumentVersion
from service.knowledge.document.parse_paths import resolve_storage_file_path


class KnowledgeStorage:
    @classmethod
    def version_dir(
        cls,
        project_id: int,
        document_id: int,
        version_label: str,
    ) -> Path:
        path = KNOWLEDGE_UPLOAD_ROOT / str(project_id) / str(document_id) / version_label
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def save_version_file(
        cls,
        *,
        project_id: int,
        document_id: int,
        version_label: str,
        file_name: str,
        content: bytes,
    ) -> str:
        dest_dir = cls.version_dir(project_id, document_id, version_label)
        dest = dest_dir / file_name
        dest.write_bytes(content)
        return str(dest.relative_to(BASE_DIR))

    @classmethod
    def absolute_path(cls, relative_path: str) -> Path:
        resolved = resolve_storage_file_path(relative_path)
        if resolved is not None:
            return resolved
        return BASE_DIR / relative_path.replace("\\", "/")

    @classmethod
    def delete_file(cls, relative_path: str | None) -> None:
        if not relative_path:
            return
        path = cls.absolute_path(relative_path)
        if path.is_file():
            path.unlink()

    @classmethod
    async def enforce_retention(cls, document_id: int, keep: int = 3) -> None:
        versions = (
            await KnowledgeDocumentVersion.filter(
                document_id=document_id,
                file_expired=False,
            )
            .exclude(file_path=None)
            .order_by("-version_seq")
        )
        to_expire = versions[keep:]
        for version in to_expire:
            cls.delete_file(version.file_path)
            version.file_path = None
            version.file_expired = True
            await version.save(update_fields=["file_path", "file_expired"])
