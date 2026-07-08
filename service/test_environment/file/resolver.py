"""测试环境管理模块 - file/resolver

resolver
"""
from copy import deepcopy
from typing import Any

from service.core.exceptions import AppException
from service.test_environment.models import EnvUploadedFile
from service.test_environment.file.storage_backend import get_storage_backend


class FileResolver:
    @classmethod
    async def resolve_file_path(
        cls,
        file_id: int,
        *,
        project_id: int | None = None,
    ) -> dict[str, str]:
        filters: dict[str, Any] = {"id": file_id, "is_deleted": False}
        if project_id is not None:
            filters["project_id"] = project_id
        record = await EnvUploadedFile.get_or_none(**filters)
        if record is None:
            raise AppException(f"上传文件 {file_id} 不存在", 404)
        path = get_storage_backend().absolute_path(record.storage_key)
        if not path.exists():
            raise AppException(f"上传文件 {file_id} 已丢失", 404)
        return {
            "absolute_path": str(path),
            "file_name": record.file_name,
            "storage_key": record.storage_key,
        }

    @classmethod
    async def resolve_request_files(
        cls, project_id: int, case_payload: dict[str, Any]
    ) -> dict[str, Any]:
        result = deepcopy(case_payload)
        request = result.get("request")
        if not isinstance(request, dict):
            return result
        files = request.get("files")
        if not isinstance(files, dict):
            return result

        resolved: dict[str, Any] = {}
        for key, val in files.items():
            if isinstance(val, dict) and "uploaded_file_id" in val:
                info = await cls.resolve_file_path(
                    val["uploaded_file_id"], project_id=project_id
                )
                resolved[key] = {
                    "path": info["absolute_path"],
                    "filename": info["file_name"],
                }
            else:
                resolved[key] = val
        request["files"] = resolved
        return result
