import json
from typing import Literal

from service.api_test.interface.models import ApiInterface
from service.api_test.interface.schemas import (
    ImportConfirmItem,
    ImportConfirmRequest,
    ImportConfirmResult,
    ImportPreviewItem,
    ImportPreviewResult,
)
from service.api_test.permissions import ensure_api_editor, ensure_api_viewer
from service.knowledge.document.parse_paths import resolve_parse_result_path
from service.core.enums import (
    ActualParseRoute,
    ApiInterfaceSource,
    KnowledgeDocType,
    ParseStatus,
)
from service.core.exceptions import AppException
from service.knowledge.document.permissions import ensure_document_viewer
from service.knowledge.document.version_service import VersionService
from service.project.models import ProjectModule
from service.user.models import User


class ImportService:
    @classmethod
    async def preview(
        cls,
        user: User,
        document_id: int,
        version_id: int,
    ) -> ImportPreviewResult:
        document = await ensure_document_viewer(document_id, user)
        if document.doc_type != KnowledgeDocType.api_doc:
            raise AppException("仅接口文档支持导入预览", 400)
        version = await VersionService.get_version_or_404(document_id, version_id)
        if version.parse_status != ParseStatus.parsed:
            raise AppException("文档版本尚未解析完成", 400)
        if not version.parse_result_path:
            raise AppException("解析结果不存在", 400)
        items = cls._load_parse_items(version.parse_result_path)
        project_id = document.project_id
        preview_items: list[ImportPreviewItem] = []
        for item in items:
            method = (item.get("method") or "").upper()
            path = item.get("path") or ""
            if not method or not path:
                continue
            existing = await ApiInterface.get_or_none(
                project_id=project_id,
                method=method,
                path=path,
                is_current=True,
            )
            preview_items.append(
                ImportPreviewItem(
                    method=method,
                    path=path,
                    summary=item.get("summary"),
                    conflict=existing is not None,
                    existing_interface_id=existing.id if existing else None,
                )
            )
        return ImportPreviewResult(
            document_id=document_id,
            version_id=version_id,
            items=preview_items,
        )

    @classmethod
    async def confirm(
        cls, user: User, data: ImportConfirmRequest
    ) -> ImportConfirmResult:
        await ensure_api_editor(data.project_id, user)
        document = await ensure_document_viewer(data.document_id, user)
        if document.doc_type != KnowledgeDocType.api_doc:
            raise AppException("仅接口文档支持导入", 400)
        if document.project_id != data.project_id:
            raise AppException("文档与项目不匹配", 400)
        version = await VersionService.get_version_or_404(
            data.document_id, data.version_id
        )
        if version.parse_status != ParseStatus.parsed:
            raise AppException("文档版本尚未解析完成", 400)
        if data.module_id is not None:
            if not await ProjectModule.filter(
                id=data.module_id, project_id=data.project_id
            ).exists():
                raise AppException("项目模块不存在", 404)

        source = cls._resolve_source(version)
        parse_items = cls._load_parse_items(version.parse_result_path)
        item_map = {
            f"{(i.get('method') or '').upper()}:{i.get('path')}": i for i in parse_items
        }

        created = updated = skipped = 0
        interface_ids: list[int] = []
        new_ids: list[int] = []

        confirm_items = data.items
        if not confirm_items:
            confirm_items = [
                ImportConfirmItem(
                    method=(i.get("method") or "").upper(),
                    path=i.get("path") or "",
                    summary=i.get("summary"),
                    parameters=i.get("parameters"),
                    request_body=i.get("requestBody"),
                    responses=i.get("responses"),
                )
                for i in parse_items
                if i.get("method") and i.get("path")
            ]

        for item in confirm_items:
            method = item.method.upper()
            path = item.path
            raw = item_map.get(f"{method}:{path}", {})
            fields = cls._map_fields(
                raw if raw else {
                    "method": method,
                    "path": path,
                    "summary": item.summary,
                    "parameters": item.parameters,
                    "requestBody": item.request_body,
                    "responses": item.responses,
                },
                source,
                data.document_id,
                data.version_id,
                data.module_id,
                data.project_id,
                data.catalog_id,
                user.id,
            )
            if fields is None:
                continue

            existing = await ApiInterface.get_or_none(
                project_id=data.project_id,
                method=method,
                path=path,
                is_current=True,
            )
            if existing is not None:
                if data.mode == "skip":
                    existing.source_document_id = data.document_id
                    existing.source_document_version_id = data.version_id
                    if data.module_id is not None:
                        existing.module_id = data.module_id
                    if data.catalog_id:
                        existing.catalog_id = data.catalog_id
                    existing.updated_by_id = user.id
                    update_fields = [
                        "source_document_id",
                        "source_document_version_id",
                        "updated_by_id",
                    ]
                    if data.module_id is not None:
                        update_fields.append("module_id")
                    if data.catalog_id:
                        update_fields.append("catalog_id")
                    await existing.save(update_fields=update_fields)
                    skipped += 1
                    interface_ids.append(existing.id)
                    continue
                for key, value in fields.items():
                    if key not in ("project_id", "method", "path", "version", "is_current"):
                        setattr(existing, key, value)
                existing.updated_by_id = user.id
                await existing.save()
                updated += 1
                interface_ids.append(existing.id)
            else:
                iface = await ApiInterface.create(**fields)
                created += 1
                interface_ids.append(iface.id)
                new_ids.append(iface.id)

        dependency_errors: list[str] = []
        if new_ids:
            from service.api_test.dependency.merge_service import DependencyMergeService

            _, errors = await DependencyMergeService.infer_and_persist(
                data.project_id, new_ids, user_id=user.id
            )
            dependency_errors.extend(errors)

        return ImportConfirmResult(
            created=created,
            updated=updated,
            skipped=skipped,
            interface_ids=interface_ids,
            dependency_inference_errors=dependency_errors,
        )

    @staticmethod
    def _load_parse_items(parse_result_path: str) -> list[dict]:
        parse_path = resolve_parse_result_path(parse_result_path)
        if parse_path is None:
            raise AppException("解析结果文件不存在", 404)
        raw = parse_path.read_text(encoding="utf-8")
        items = json.loads(raw) if raw.strip() else []
        if not isinstance(items, list):
            raise AppException("解析结果格式无效", 400)
        return items

    @staticmethod
    def _resolve_source(version) -> ApiInterfaceSource:
        if version.actual_parse_route == ActualParseRoute.openapi:
            return ApiInterfaceSource.openapi
        return ApiInterfaceSource.swagger

    @staticmethod
    def _map_fields(
        item: dict,
        source: ApiInterfaceSource,
        source_document_id: int,
        source_document_version_id: int,
        module_id: int | None,
        project_id: int,
        catalog_id: int,
        user_id: int,
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
            "catalog_id": catalog_id,
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
            "source_document_version_id": source_document_version_id,
            "version": 1,
            "is_current": True,
            "created_by_id": user_id,
            "updated_by_id": user_id,
        }
