from datetime import datetime, timezone
from pathlib import Path

from fastapi.responses import FileResponse

from service.core.config import BASE_DIR, MAX_UPLOAD_BYTES
from service.core.exceptions import AppException
from service.core.pagination import paginate
from service.test_environment.models import EnvUploadedFile
from service.test_environment.permissions import ensure_project_editor, ensure_project_viewer
from service.test_environment.file.resolver import FileResolver
from service.test_environment.file.schemas import (
    PaginatedUploadedFiles,
    UploadedFileBrief,
    UploadedFilePathResolved,
)
from service.test_environment.file.storage_backend import get_storage_backend
from service.user.models import User

UPLOAD_ROOT = BASE_DIR / "test_data" / "files"


class UploadedFileService:
    @classmethod
    def _storage_dir(cls, project_id: int) -> Path:
        path = UPLOAD_ROOT / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def _storage_key(cls, project_id: int, file_name: str) -> str:
        return str((UPLOAD_ROOT / str(project_id) / file_name).relative_to(BASE_DIR))

    @classmethod
    async def list_files(
        cls,
        user: User,
        project_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedUploadedFiles:
        await ensure_project_viewer(project_id, user)
        qs = EnvUploadedFile.filter(project_id=project_id, is_deleted=False).order_by(
            "-updated_at"
        )
        total, items = await paginate(qs, page, page_size)
        return PaginatedUploadedFiles(
            total=total,
            page=page,
            page_size=page_size,
            items=[cls._to_brief(f) for f in items],
        )

    @classmethod
    async def upload(
        cls,
        user: User,
        project_id: int,
        *,
        file_name: str,
        content: bytes,
        mime_type: str | None,
    ) -> UploadedFileBrief:
        await ensure_project_editor(project_id, user)
        if len(content) > MAX_UPLOAD_BYTES:
            raise AppException(
                f"文件大小超过限制 {MAX_UPLOAD_BYTES} 字节", 400
            )
        existing = await EnvUploadedFile.get_or_none(
            project_id=project_id, file_name=file_name, is_deleted=False
        )
        if existing:
            raise AppException("同名文件已存在，请先删除或使用其他名称", 409)
        soft_deleted = await EnvUploadedFile.get_or_none(
            project_id=project_id, file_name=file_name, is_deleted=True
        )
        storage_key = cls._storage_key(project_id, file_name)
        get_storage_backend().write(storage_key, content)
        if soft_deleted:
            soft_deleted.storage_key = storage_key
            soft_deleted.file_size = len(content)
            soft_deleted.mime_type = mime_type
            soft_deleted.is_deleted = False
            soft_deleted.deleted_at = None
            soft_deleted.uploaded_by_id = user.id
            await soft_deleted.save()
            return cls._to_brief(soft_deleted)
        record = await EnvUploadedFile.create(
            project_id=project_id,
            file_name=file_name,
            storage_key=storage_key,
            file_size=len(content),
            mime_type=mime_type,
            uploaded_by_id=user.id,
        )
        return cls._to_brief(record)

    @classmethod
    async def soft_delete(cls, user: User, file_id: int) -> None:
        record = await EnvUploadedFile.get_or_none(id=file_id, is_deleted=False)
        if record is None:
            raise AppException("文件不存在", 404)
        await ensure_project_editor(record.project_id, user)
        record.is_deleted = True
        record.deleted_at = datetime.now(timezone.utc)
        await record.save()

    @classmethod
    async def resolve_path(cls, user: User, file_id: int) -> UploadedFilePathResolved:
        record = await EnvUploadedFile.get_or_none(id=file_id, is_deleted=False)
        if record is None:
            raise AppException("文件不存在", 404)
        await ensure_project_viewer(record.project_id, user)
        info = await FileResolver.resolve_file_path(file_id, project_id=record.project_id)
        return UploadedFilePathResolved(**info)

    @classmethod
    async def download(cls, user: User, file_id: int) -> FileResponse:
        record = await EnvUploadedFile.get_or_none(id=file_id, is_deleted=False)
        if record is None:
            raise AppException("文件不存在", 404)
        await ensure_project_viewer(record.project_id, user)
        path = get_storage_backend().absolute_path(record.storage_key)
        if not path.exists():
            raise AppException("文件已丢失", 404)
        return FileResponse(
            path=str(path),
            filename=record.file_name,
            media_type=record.mime_type or "application/octet-stream",
        )

    @staticmethod
    def _to_brief(record: EnvUploadedFile) -> UploadedFileBrief:
        return UploadedFileBrief(
            id=record.id,
            project_id=record.project_id,
            file_name=record.file_name,
            file_size=record.file_size,
            mime_type=record.mime_type,
            uploaded_by_id=record.uploaded_by_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
