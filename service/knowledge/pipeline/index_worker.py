import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from service.core.config import BASE_DIR, KNOWLEDGE_PARSE_ROOT
from service.core.enums import (
    ActualParseRoute,
    IndexStatus,
    KnowledgeDocType,
    ParseMode,
    ParseStatus,
)
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.document.storage import KnowledgeStorage
from service.knowledge.document.parse_enrich import merge_raw_with_display
from service.knowledge.downstream.requirement_sync import sync_requirement_candidate
from service.knowledge.pipeline.rag_gateway import RagGateway
from service.knowledge.rules.file_rules import detect_api_spec_kind
from service.knowledge.rules.parse_router import resolve_parse_route
from utils.parser.openapi_document_parser import parse_openapi_file
from utils.parser.swagger_document_parser import parse_swagger_file

logger = logging.getLogger(__name__)

_AI_ROUTES = {
    ActualParseRoute.ai_text,
    ActualParseRoute.ai_multimodal,
    ActualParseRoute.auto_text,
}


class IndexWorker:
    _tasks: set[asyncio.Task] = set()

    @classmethod
    def schedule(cls, version_id: int) -> asyncio.Task:
        task = asyncio.create_task(cls._run_version(version_id))
        cls._tasks.add(task)
        task.add_done_callback(cls._tasks.discard)
        return task

    @classmethod
    async def _run_version(cls, version_id: int) -> None:
        try:
            await cls.process_version(version_id)
        except Exception:
            logger.exception("知识库版本 %s 索引/解析失败", version_id)

    @classmethod
    async def start_processing(
        cls,
        version_id: int,
        *,
        doc_type: KnowledgeDocType,
        parse_mode: ParseMode,
        content: bytes,
    ) -> None:
        """接口规范文件同步解析，其余文档异步索引（避免 create_task 被 GC 或未调度）。"""
        if cls._should_process_inline(doc_type, parse_mode, content):
            await cls.process_version(version_id)
        else:
            cls.schedule(version_id)

    @staticmethod
    def _should_process_inline(
        doc_type: KnowledgeDocType,
        parse_mode: ParseMode,
        content: bytes,
    ) -> bool:
        if doc_type != KnowledgeDocType.api_doc:
            return False
        if parse_mode in (ParseMode.swagger, ParseMode.openapi):
            return True
        return detect_api_spec_kind(content) in ("swagger", "openapi")

    @classmethod
    async def process_version(cls, version_id: int) -> None:
        version = await KnowledgeDocumentVersion.get_or_none(id=version_id)
        if version is None or version.index_status != IndexStatus.pending:
            return

        document = await KnowledgeDocument.get_or_none(id=version.document_id)
        if document is None:
            return

        if version.file_expired or not version.file_path:
            await cls._mark_index_failed(version, "文件已过期或不存在")
            return

        abs_path = KnowledgeStorage.absolute_path(version.file_path)
        if not abs_path.is_file():
            version.file_expired = True
            await version.save(update_fields=["file_expired"])
            await cls._mark_index_failed(version, "文件已丢失")
            return

        content = abs_path.read_bytes()
        route = resolve_parse_route(
            file_name=version.file_name,
            doc_type=document.doc_type,
            parse_mode=document.parse_mode,
            content=content,
        )
        version.actual_parse_route = route
        await version.save(update_fields=["actual_parse_route"])

        try:
            if route in _AI_ROUTES:
                await cls._process_rag(version, document, str(abs_path), route)
            elif route == ActualParseRoute.swagger:
                await cls._process_swagger(version, document, abs_path)
            elif route == ActualParseRoute.openapi:
                await cls._process_openapi(version, document, abs_path)
        except Exception as exc:
            err = str(exc) or repr(exc)
            if route in (ActualParseRoute.swagger, ActualParseRoute.openapi):
                await cls._mark_parse_failed(version, err)
            else:
                await cls._mark_index_failed(version, err)

    @classmethod
    async def _process_rag(
        cls,
        version: KnowledgeDocumentVersion,
        document: KnowledgeDocument,
        abs_path: str,
        route: ActualParseRoute,
    ) -> None:
        workspace = await document.workspace

        version.index_status = IndexStatus.indexing
        version.index_error = None
        await version.save(update_fields=["index_status", "index_error"])

        if version.rag_doc_id and version.rag_backend:
            await RagGateway.delete(
                workspace_key=workspace.workspace_key,
                rag_doc_id=version.rag_doc_id,
                rag_backend=version.rag_backend,
            )

        doc_id = f"knowledge/{document.id}/{version.id}"
        if route == ActualParseRoute.ai_multimodal:
            rag_backend, rag_doc_id = await RagGateway.index_multimodal(
                workspace_key=workspace.workspace_key,
                absolute_path=abs_path,
                doc_id=doc_id,
            )
        else:
            rag_backend, rag_doc_id = await RagGateway.index_text(
                workspace_key=workspace.workspace_key,
                absolute_path=abs_path,
                doc_id=doc_id,
            )

        version.rag_backend = rag_backend
        version.rag_doc_id = rag_doc_id
        version.index_status = IndexStatus.indexed
        version.indexed_at = datetime.now(timezone.utc)
        version.index_error = None
        await version.save(
            update_fields=[
                "rag_backend",
                "rag_doc_id",
                "index_status",
                "indexed_at",
                "index_error",
            ]
        )

        await cls._activate_version(version, document)

        if document.doc_type == KnowledgeDocType.requirement:
            await sync_requirement_candidate(document, version)

    @classmethod
    async def _process_swagger(
        cls,
        version: KnowledgeDocumentVersion,
        document: KnowledgeDocument,
        abs_path: Path,
    ) -> None:
        await cls._process_spec_parse(
            version,
            document,
            abs_path,
            parse_fn=parse_swagger_file,
        )

    @classmethod
    async def _process_openapi(
        cls,
        version: KnowledgeDocumentVersion,
        document: KnowledgeDocument,
        abs_path: Path,
    ) -> None:
        await cls._process_spec_parse(
            version,
            document,
            abs_path,
            parse_fn=parse_openapi_file,
        )

    @classmethod
    async def _process_spec_parse(
        cls,
        version: KnowledgeDocumentVersion,
        document: KnowledgeDocument,
        abs_path: Path,
        *,
        parse_fn,
    ) -> None:
        version.index_status = IndexStatus.parsing
        version.parse_status = ParseStatus.parsing
        version.index_error = None
        version.parse_error = None
        await version.save(
            update_fields=["index_status", "parse_status", "index_error", "parse_error"]
        )

        parsed = await asyncio.to_thread(parse_fn, abs_path)
        relative_path = cls._save_parse_result(
            project_id=document.project_id,
            document_id=document.id,
            version_label=version.version_label,
            data=parsed,
        )

        version.parse_status = ParseStatus.parsed
        version.parse_result_path = relative_path
        version.parse_error = None
        version.index_status = IndexStatus.na
        version.index_error = None
        await version.save(
            update_fields=[
                "parse_status",
                "parse_result_path",
                "parse_error",
                "index_status",
                "index_error",
            ]
        )
        await cls._activate_version(version, document)

    @classmethod
    def _save_parse_result(
        cls,
        *,
        project_id: int,
        document_id: int,
        version_label: str,
        data: list,
    ) -> str:
        dest_dir = (
            KNOWLEDGE_PARSE_ROOT / str(project_id) / str(document_id) / version_label
        )
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "parsed.json"
        enriched = [
            merge_raw_with_display(item) for item in data if isinstance(item, dict)
        ]
        dest.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(dest.relative_to(BASE_DIR))

    @classmethod
    async def _activate_version(
        cls,
        version: KnowledgeDocumentVersion,
        document: KnowledgeDocument,
    ) -> None:
        current = None
        if document.current_version_id:
            current = await KnowledgeDocumentVersion.get_or_none(
                id=document.current_version_id
            )

        should_switch = False
        if current is None:
            should_switch = True
        elif current.id == version.id:
            should_switch = False
        elif version.version_seq > current.version_seq:
            should_switch = True
        elif current.index_status == IndexStatus.pending:
            should_switch = True

        if should_switch:
            if current is not None and current.id != version.id:
                if current.rag_doc_id and current.rag_backend:
                    workspace = await document.workspace
                    await RagGateway.delete(
                        workspace_key=workspace.workspace_key,
                        rag_doc_id=current.rag_doc_id,
                        rag_backend=current.rag_backend,
                    )
            if current is None or current.id != version.id:
                document.current_version_id = version.id
                document.updated_at = datetime.now(timezone.utc)
                await document.save(update_fields=["current_version_id", "updated_at"])

    @classmethod
    async def _mark_index_failed(
        cls,
        version: KnowledgeDocumentVersion,
        message: str,
    ) -> None:
        version.index_status = IndexStatus.failed
        version.index_error = message
        await version.save(update_fields=["index_status", "index_error"])

    @classmethod
    async def _mark_parse_failed(
        cls,
        version: KnowledgeDocumentVersion,
        message: str,
    ) -> None:
        version.index_status = IndexStatus.failed
        version.parse_status = ParseStatus.failed
        version.index_error = message
        version.parse_error = message
        await version.save(
            update_fields=["index_status", "parse_status", "index_error", "parse_error"]
        )
