"""知识库管理模块 - pipeline/rag_gateway

网关
"""
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from service.core.enums import RagBackend

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from service.ai_engine.rag.ragManager import RAGManager
    from service.ai_engine.rag.rag_api import RAGClient


class RagGateway:
    """rag网关"""
    _managers: dict[str, "RAGManager"] = {}
    _client: "RAGClient | None" = None

    @classmethod
    def _get_client(cls) -> "RAGClient":
        if cls._client is None:
            from service.ai_engine.rag.rag_api import RAGClient

            cls._client = RAGClient()
        return cls._client

    @classmethod
    def _get_manager_cls(cls):
        from service.ai_engine.rag.ragManager import RAGManager

        return RAGManager

    @classmethod
    def is_remote_available(cls) -> bool:
        try:
            return cls._get_client().health_check()
        except Exception:
            return False

    @classmethod
    async def _get_manager(cls, workspace_key: str) -> "RAGManager":
        manager = cls._managers.get(workspace_key)
        if manager is None:
            manager = cls._get_manager_cls()()
            logger.info("初始化 RAGManager workspace=%s", workspace_key)
            await manager.init_rag(workspace_key)
            cls._managers[workspace_key] = manager
            logger.info("RAGManager 初始化完成 workspace=%s", workspace_key)
        return manager

    @classmethod
    async def submit_text(
        cls,
        *,
        workspace_key: str,
        absolute_path: str,
        doc_id: str,
    ) -> tuple[RagBackend, str]:
        """提交文本到 RAG，返回 (backend, rag_doc_id)。不等待索引完成。"""
        if cls.is_remote_available():
            text = await asyncio.to_thread(
                Path(absolute_path).read_text, encoding="utf-8"
            )
            rag_doc_id = await asyncio.to_thread(
                cls._get_client().insert_text,
                text,
                doc_id,
                workspace_key,
            )
            return RagBackend.rag_client, rag_doc_id
        logger.info("RAGManager.index_text 开始 path=%s", absolute_path)
        manager = await cls._get_manager(workspace_key)
        await manager.add_document(absolute_path)
        logger.info("RAGManager.index_text 完成 path=%s", absolute_path)
        return RagBackend.rag_manager, absolute_path

    @classmethod
    async def wait_indexing(
        cls,
        rag_doc_id: str,
        workspace_key: str,
        *,
        poll_interval: float = 3.0,
        timeout: float = 300.0,
    ) -> None:
        """Poll LightRAG server until the document is fully indexed.

        Raises TimeoutError if indexing takes too long,
        or RuntimeError if the server reports an error.
        本地 RAGManager 模式为同步处理，无需轮询，直接返回。
        """
        if not cls.is_remote_available():
            return
        import time
        start = time.monotonic()
        while True:
            status = await asyncio.to_thread(
                cls._get_client().get_doc_status, rag_doc_id, workspace_key
            )
            logger.info("[RAG] doc=%s status=%s", rag_doc_id, status)

            if status == "processed":
                return
            if status in ("error", "failed"):
                raise RuntimeError(f"LightRAG 索引失败: doc_id={rag_doc_id}")

            elapsed = time.monotonic() - start
            if elapsed > timeout:
                raise TimeoutError(
                    f"LightRAG 索引超时 ({timeout}s): doc_id={rag_doc_id}, last_status={status}"
                )

            await asyncio.sleep(poll_interval)

    @classmethod
    async def submit_multimodal(
        cls,
        *,
        workspace_key: str,
        absolute_path: str,
        doc_id: str,
    ) -> tuple[RagBackend, str]:
        """提交多模态文档到 RAG，返回 (backend, rag_doc_id)。不等待索引完成。"""
        if cls.is_remote_available():
            rag_doc_id = await asyncio.to_thread(
                cls._get_client().upload_document,
                absolute_path,
                workspace_key,
            )
            return RagBackend.rag_client, rag_doc_id
        logger.info("RAGManager.index_multimodal 开始 path=%s", absolute_path)
        manager = await cls._get_manager(workspace_key)
        await manager.load_document(absolute_path)
        logger.info("RAGManager.index_multimodal 完成 path=%s", absolute_path)
        return RagBackend.rag_manager, absolute_path

    @classmethod
    async def delete(
        cls,
        *,
        workspace_key: str,
        rag_doc_id: str,
        rag_backend: RagBackend,
    ) -> None:
        if not rag_doc_id:
            return
        try:
            if rag_backend == RagBackend.rag_client and cls.is_remote_available():
                # 按 file_source 查找 LightRAG 内部 hash ID 后删除
                await asyncio.to_thread(
                    cls._get_client().delete_by_file_sources,
                    [rag_doc_id],
                    workspace_key,
                )
                return
            if rag_backend == RagBackend.rag_manager:
                manager = await cls._get_manager(workspace_key)
                await manager.delete_document(rag_doc_id)
        except Exception:
            logger.warning("RAG 删除失败 doc_id=%s", rag_doc_id, exc_info=True)

    @classmethod
    async def query(cls, workspace_key: str, question: str) -> str:
        if cls.is_remote_available():
            result = await asyncio.to_thread(
                cls._get_client().query,
                question,
                None,
                10,
                workspace_key,
            )
            if isinstance(result, dict):
                return str(result.get("response") or result)
            return str(result)
        manager = await cls._get_manager(workspace_key)
        return await manager.query(question)

    @classmethod
    def query_stream(cls, workspace_key: str, question: str):
        """Sync stream for MCP tools; remote RAG only."""
        yield from cls._get_client().query_stream(
            question,
            workspace_key=workspace_key,
        )
