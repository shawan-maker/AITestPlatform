import json
from pathlib import Path
from typing import Literal

from service.api_test.models import ApiInterface
from service.core.config import BASE_DIR
from service.core.enums import (
    ActualParseRoute,
    ApiInterfaceSource,
    KnowledgeDocType,
    ParseStatus,
)
from service.core.exceptions import AppException
from service.knowledge.permissions import ensure_document_editor
from service.knowledge.schemas import ImportInterfacesResult
from service.knowledge.version_service import VersionService
from service.project.models import ProjectModule
from service.user.models import User

_API_VERSION = 1


class ImportService:
    @classmethod
    async def import_interfaces(
        cls,
        user: User,
        document_id: int,
        version_id: int,
        module_id: int,
        import_mode: Literal["skip", "upsert"] = "skip",
    ) -> ImportInterfacesResult:
        document = await ensure_document_editor(document_id, user)
        if document.doc_type != KnowledgeDocType.api_doc:
            raise AppException("仅接口文档支持导入接口", 400)

        version = await VersionService.get_version_or_404(document_id, version_id)
        if version.parse_status != ParseStatus.parsed:
            raise AppException("文档版本尚未解析完成", 400)
        if not version.parse_result_path:
            raise AppException("解析结果不存在", 400)

        if not await ProjectModule.filter(
            id=module_id, project_id=document.project_id
        ).exists():
            raise AppException("项目模块不存在", 404)

        parse_path = Path(BASE_DIR) / version.parse_result_path
        if not parse_path.is_file():
            raise AppException("解析结果文件不存在", 404)

        raw = parse_path.read_text(encoding="utf-8")
        items = json.loads(raw) if raw.strip() else []
        if not isinstance(items, list):
            raise AppException("解析结果格式无效", 400)

        source = cls._resolve_source(version)
        project_id = document.project_id
        created = updated = skipped = 0
        interface_ids: list[int] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            fields = cls._map_item(item, source, document.id, module_id, project_id)
            if fields is None:
                continue

            existing = await ApiInterface.get_or_none(
                project_id=project_id,
                method=fields["method"],
                path=fields["path"],
                version=_API_VERSION,
            )
            if existing is not None:
                if import_mode == "skip":
                    skipped += 1
                    interface_ids.append(existing.id)
                    continue
                for key, value in fields.items():
                    setattr(existing, key, value)
                await existing.save()
                updated += 1
                interface_ids.append(existing.id)
            else:
                iface = await ApiInterface.create(**fields, version=_API_VERSION)
                created += 1
                interface_ids.append(iface.id)

        return ImportInterfacesResult(
            created=created,
            updated=updated,
            skipped=skipped,
            interface_ids=interface_ids,
        )

    @staticmethod
    def _resolve_source(version) -> ApiInterfaceSource:
        if version.actual_parse_route == ActualParseRoute.openapi:
            return ApiInterfaceSource.openapi
        return ApiInterfaceSource.swagger

    @staticmethod
    def _map_item(
        item: dict,
        source: ApiInterfaceSource,
        source_document_id: int,
        module_id: int,
        project_id: int,
    ) -> dict | None:
        path = item.get("path") or ""
        method = (item.get("method") or "").upper()
        if not path or not method:
            return None
        summary = item.get("summary")
        if summary is not None:
            summary = str(summary)[:255]
        return {
            "project_id": project_id,
            "module_id": module_id,
            "method": method,
            "path": path,
            "summary": summary,
            "parameters": item.get("parameters")
            or {"header": [], "path": [], "query": []},
            "request_body": item.get("requestBody"),
            "responses": item.get("responses") or [],
            "source": source,
            "source_document_id": source_document_id,
        }
