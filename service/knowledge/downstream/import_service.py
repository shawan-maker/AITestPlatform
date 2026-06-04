from typing import Literal

from service.api_test.interface.import_service import ImportService as ApiTestImportService
from service.api_test.interface.models import ApiInterfaceCatalog
from service.api_test.interface.schemas import ImportConfirmItem, ImportConfirmRequest
from service.core.enums import KnowledgeDocType, ParseStatus
from service.core.exceptions import AppException
from service.knowledge.document.permissions import ensure_document_editor
from service.knowledge.document.version_service import VersionService
from service.knowledge.document.import_marker import mark_interfaces_imported
from service.knowledge.downstream.schemas import ImportInterfacesRequest, ImportInterfacesResult
from service.project.models import ProjectModule
from service.user.models import User


class ImportService:
    @classmethod
    async def preview_interfaces(
        cls,
        user: User,
        document_id: int,
        version_id: int,
    ):
        return await ApiTestImportService.preview(user, document_id, version_id)

    @classmethod
    async def import_interfaces(
        cls,
        user: User,
        document_id: int,
        version_id: int,
        body: ImportInterfacesRequest,
    ) -> ImportInterfacesResult:
        document = await ensure_document_editor(document_id, user)
        if document.doc_type != KnowledgeDocType.api_doc:
            raise AppException("仅接口文档支持导入接口", 400)

        version = await VersionService.get_version_or_404(document_id, version_id)
        if version.parse_status != ParseStatus.parsed:
            raise AppException("文档版本尚未解析完成", 400)
        if not version.parse_result_path:
            raise AppException("解析结果不存在", 400)

        if body.module_id is not None:
            if not await ProjectModule.filter(
                id=body.module_id, project_id=document.project_id
            ).exists():
                raise AppException("项目模块不存在", 404)

        resolved_catalog_id = body.catalog_id
        if resolved_catalog_id is None:
            default_cat = await ApiInterfaceCatalog.get_or_none(
                project_id=document.project_id, parent_id=None, name="默认"
            )
            if default_cat is None:
                default_cat = await ApiInterfaceCatalog.create(
                    project_id=document.project_id,
                    name="默认",
                    level=1,
                )
            resolved_catalog_id = default_cat.id

        if body.items:
            items = [
                ImportConfirmItem(
                    method=(i.get("method") or "").upper(),
                    path=i.get("path") or "",
                    summary=i.get("summary"),
                    parameters=i.get("parameters"),
                    request_body=i.get("requestBody") or i.get("request_body"),
                    responses=i.get("responses"),
                )
                for i in body.items
                if i.get("method") and i.get("path")
            ]
        else:
            items_raw = ApiTestImportService._load_parse_items(version.parse_result_path)
            items = [
                ImportConfirmItem(
                    method=(i.get("method") or "").upper(),
                    path=i.get("path") or "",
                    summary=i.get("summary"),
                    parameters=i.get("parameters"),
                    request_body=i.get("requestBody"),
                    responses=i.get("responses"),
                )
                for i in items_raw
                if i.get("method") and i.get("path")
            ]

        result = await ApiTestImportService.confirm(
            user,
            ImportConfirmRequest(
                project_id=document.project_id,
                catalog_id=resolved_catalog_id,
                module_id=body.module_id,
                document_id=document_id,
                version_id=version_id,
                mode=body.import_mode,
                items=items,
            ),
        )
        mark_interfaces_imported(version.parse_result_path)
        return ImportInterfacesResult(
            created=result.created,
            updated=result.updated,
            skipped=result.skipped,
            interface_ids=result.interface_ids,
        )
