import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
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
from service.knowledge.pipeline.rag_gateway import RagGateway
from service.knowledge.rules.file_rules import detect_api_spec_kind
from service.knowledge.rules.parse_router import resolve_parse_route
from utils.parser.openapi_document_parser import parse_openapi_file
from utils.parser.swagger_document_parser import parse_swagger_file
from utils.parser.api_document_ai_parser import APIDocumentParser

logger = logging.getLogger(__name__)

_AI_ROUTES = {
    ActualParseRoute.ai_text,
    ActualParseRoute.ai_multimodal,
    ActualParseRoute.auto_text,
}

_TIMEOUT_MINUTES = 10


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
        inline = cls._should_process_inline(doc_type, parse_mode, content)
        kind = detect_api_spec_kind(content)
        if inline:
            await cls.process_version(version_id)
        else:
            cls.schedule(version_id)
    def _should_process_inline(
        doc_type: KnowledgeDocType,
        parse_mode: ParseMode,
        content: bytes,
    ) -> bool:
        # AI 解析模式始终走异步，不管内容是否像 Swagger/OpenAPI
        if parse_mode == ParseMode.ai:
            return False
        if doc_type != KnowledgeDocType.api_doc:
            return False
        if parse_mode in (ParseMode.swagger, ParseMode.openapi):
            return True
        return detect_api_spec_kind(content) in ("swagger", "openapi")

    @classmethod
    async def process_version(cls, version_id: int) -> None:
        version = await KnowledgeDocumentVersion.get_or_none(id=version_id)
        if version is None:
            return

        # 超时检测：indexing / parsing 超过 _TIMEOUT_MINUTES 分钟自动标记为失败
        if version.index_status in (IndexStatus.indexing, IndexStatus.parsing):
            await cls._check_timeout(version)

        if version.index_status != IndexStatus.pending:
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
        try:
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
            # 对 API 文档类型，额外执行 AI 结构化解析以提取接口数据
            if document.doc_type == KnowledgeDocType.api_doc:
                await cls._process_ai_parse(version, document, abs_path)

            await cls._activate_version(version, document)

        except Exception as exc:
            logger.exception("RAG 处理失败 document=%s version=%s route=%s", document.id, version.id, route)
            err_msg = str(exc) or repr(exc) or "RAG 处理未知错误"
            try:
                await cls._mark_index_failed(version, err_msg)
            except Exception as save_err:
                logger.error("标记 index_status=failed 也失败了 version=%s: %s", version.id, save_err)
                # 二次兜底：只保存最核心的状态字段
                try:
                    version.index_status = IndexStatus.failed
                    version.index_error = err_msg
                    await version.save(update_fields=["index_status", "index_error"])
                except Exception:
                    logger.critical("版本 %s 状态回滚完全失败，状态可能卡在 indexing", version.id)
            raise

    @classmethod
    async def _process_ai_parse(
        cls,
        version: KnowledgeDocumentVersion,
        document: KnowledgeDocument,
        abs_path: str,
    ) -> None:
        """RAG 索引成功后，额外用 AI 提取结构化接口数据（仅 api_doc 类型）。"""
        version.parse_status = ParseStatus.parsing
        version.parse_error = None
        await version.save(update_fields=["parse_status", "parse_error"])

        try:
            file_path = Path(abs_path)
            # 读取文件文本内容作为 AI 解析输入
            raw_text = file_path.read_text(encoding="utf-8", errors="replace")

            # 调用 AI Parser 提取接口数据（同步阻塞，放入线程池）
            parsed = await asyncio.to_thread(
                APIDocumentParser().api_parser, raw_text
            )

            if not isinstance(parsed, list):
                parsed = [parsed] if isinstance(parsed, dict) else []

            # 保存解析结果（复用 _save_parse_result）
            relative_path = cls._save_parse_result(
                project_id=document.project_id,
                document_id=document.id,
                version_label=version.version_label,
                data=parsed,
            )

            version.parse_status = ParseStatus.parsed
            version.parse_result_path = relative_path
            version.parse_error = None
            await version.save(
                update_fields=["parse_status", "parse_result_path", "parse_error"]
            )
        except Exception as exc:
            logger.exception("AI 结构化解析失败 document=%s version=%s", document.id, version.id)
            err_msg = str(exc) or repr(exc) or "AI 结构化解析未知错误"
            version.parse_status = ParseStatus.failed
            version.parse_error = err_msg
            try:
                await version.save(update_fields=["parse_status", "parse_error"])
            except Exception:
                logger.error("保存 AI 解析失败状态也失败了 version=%s", version.id)

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
    async def detect_and_fail_timeouts(cls) -> None:
        """扫描所有 indexing/parsing 状态的版本，将超时的标记为 failed。"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=_TIMEOUT_MINUTES)
        stale = await KnowledgeDocumentVersion.filter(
            index_status__in=[IndexStatus.indexing, IndexStatus.parsing],
        )
        for v in stale:
            # 用 created_at 作为近似时间（进入 indexing/parsing 后不再更新此字段）
            since = v.created_at
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)
            if since < cutoff:
                logger.warning(
                    "检测到超时版本 %s（状态=%s），自动标记为解析失败",
                    v.id,
                    v.index_status,
                )
                await cls._mark_index_failed(v, f"解析超时（超过{_TIMEOUT_MINUTES}分钟未完成）")

    @classmethod
    async def _check_timeout(cls, version: KnowledgeDocumentVersion) -> None:
        """检测版本是否处理超时，超时则自动标记为 failed。"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=_TIMEOUT_MINUTES)
        # 用 created_at 作为进入当前状态的近似时间
        since = version.created_at
        if since is None:
            return
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        if since < cutoff:
            logger.warning(
                "版本 %s 状态 %s 已超过 %d 分钟，自动标记为解析失败",
                version.id,
                version.index_status,
                _TIMEOUT_MINUTES,
            )
            await cls._mark_index_failed(version, f"解析超时（超过{_TIMEOUT_MINUTES}分钟未完成）")

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
