import json
from typing import Literal

from service.api_test.interface.models import ApiInterface, ApiInterfaceCatalog
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
    @staticmethod
    def _enum_value(value) -> str | None:
        if value is None:
            return None
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    async def _collect_catalog_descendants(
        project_id: int, catalog_id: int
    ) -> list[int]:
        """v2: 获取目标目录及其所有子目录ID列表"""
        catalogs = await ApiInterfaceCatalog.filter(
            project_id=project_id
        ).values("id", "parent_id")
        children_map: dict[int | None, list[int]] = {}
        for row in catalogs:
            children_map.setdefault(row["parent_id"], []).append(row["id"])
        result: set[int] = {catalog_id}
        stack = [catalog_id]
        while stack:
            cid = stack.pop()
            for child_id in children_map.get(cid, []):
                if child_id not in result:
                    result.add(child_id)
                    stack.append(child_id)
        return list(result)

    @classmethod
    async def preview(
        cls,
        user: User,
        document_id: int,
        version_id: int,
        *,
        catalog_id: int | None = None,
    ) -> ImportPreviewResult:
        from service.core.enums import IndexStatus

        document = await ensure_document_viewer(document_id, user)
        if document.doc_type != KnowledgeDocType.api_doc:
            raise AppException("仅接口文档支持导入预览", 400)
        version = await VersionService.get_version_or_404(document_id, version_id)

        # 结构化解析完成：加载解析结果
        if version.parse_status == ParseStatus.parsed and version.parse_result_path:
            items = cls._load_parse_items(version.parse_result_path)
        # AI 解析完成但无结构化数据：返回空列表（提示用户无接口可导入）
        elif cls._enum_value(version.index_status) in (IndexStatus.indexed.value, IndexStatus.na.value):
            items = []
        else:
            raise AppException("文档版本尚未解析完成", 400)
        project_id = document.project_id

        # 收集目标目录范围（用于目录级冲突检测）
        target_catalog_ids: list[int] | None = None
        if catalog_id is not None:
            target_catalog_ids = await cls._collect_catalog_descendants(project_id, catalog_id)

        preview_items: list[ImportPreviewItem] = []
        for item in items:
            method = (item.get("method") or "").upper()
            path = item.get("path") or ""
            if not method or not path:
                continue

            # 冲突检测：若指定了目录，仅在目录范围内检测；否则全局检测
            # 使用 .filter().first() 而非 get_or_none，因为同(method,path)可能有多条记录
            if target_catalog_ids is not None:
                existing = await ApiInterface.filter(
                    project_id=project_id,
                    catalog_id__in=target_catalog_ids,
                    method=method,
                    path=path,
                    is_current=True,
                ).first()
            else:
                existing = await ApiInterface.filter(
                    project_id=project_id,
                    method=method,
                    path=path,
                    is_current=True,
                ).first()
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
        """v3: 知识库re-import模式。不允许覆盖现有接口；目标目录(含子树)有相同(method,path)的current接口则整体失败"""
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

        # 获取目标目录及其所有子目录ID
        target_catalog_ids = await cls._collect_catalog_descendants(
            data.project_id, data.catalog_id
        )

        source = cls._resolve_source(version)
        parse_items = cls._load_parse_items(version.parse_result_path)
        item_map = {
            f"{(i.get('method') or '').upper()}:{i.get('path')}": i for i in parse_items
        }

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

        # 冲突检查：仅在目标目录（含子树）范围内检查重复接口
        # 同一 (method, path) 只要不在同一目标目录下就允许导入
        conflicts: list[dict] = []
        for item in confirm_items:
            method = item.method.upper()
            path = item.path
            # 目录范围检查：只在目标目录及其子目录中查找重复
            existing_in_catalog = await ApiInterface.get_or_none(
                project_id=data.project_id,
                catalog_id__in=target_catalog_ids,
                method=method,
                path=path,
                is_current=True,
            )
            if existing_in_catalog is not None:
                conflicts.append({
                    "method": method,
                    "path": path,
                    "existing_interface_id": existing_in_catalog.id,
                })

        if conflicts:
            conflict_list = "; ".join(
                f"{c['method']} {c['path']}" for c in conflicts
            )
            raise AppException(
                f"目标目录中已存在重复接口，无法导入: {conflict_list}。请选择其他目录或手动去重。",
                code=409,
            )

        # 无冲突，执行创建
        created = 0
        interface_ids: list[int] = []
        new_ids: list[int] = []

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

            # 处理 DB 唯一约束 (project_id, method, path, version)：
            # 应用层已按目录范围检查过，但项目其他目录可能有同名接口（version=1）
            # 此时自动递增版本号以允许跨目录导入同名接口
            from tortoise.exceptions import IntegrityError as TortoiseIntegrityError
            iface = None
            for attempt_version in range(1, 100):
                fields["version"] = attempt_version
                try:
                    iface = await ApiInterface.create(**fields)
                    break
                except TortoiseIntegrityError:
                    # 唯一键冲突 → 继续尝试下一版本号
                    continue

            if iface is None:
                # 99 次都冲突（极端情况），跳过该接口
                continue

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
            failed=0,
            conflicts=[],
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
        if version.actual_parse_route in (
            ActualParseRoute.ai_text,
            ActualParseRoute.ai_multimodal,
            ActualParseRoute.auto_text,
        ):
            return ApiInterfaceSource.rag
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
