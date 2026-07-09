import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_BASE_DIR / ".env")


class RAGClient:
    """通过 HTTP 接入 LightRAG Server。"""

    def __init__(self, timeout: float | None = None):
        self.timeout = timeout or float(os.getenv("RAG_CLIENT_TIMEOUT", "60"))
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": os.getenv("RAG_API_KEY") or "",
        }
        self.url = (os.getenv("RAG_SERVER_URL") or "").rstrip("/")

    def _available(self) -> bool:
        return bool(self.url)

    def health_check(self, timeout: float = 2.0) -> bool:
        if not self._available():
            return False
        try:
            resp = requests.get(f"{self.url}/health", headers=self.headers, timeout=timeout)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def _workspace_headers(self, workspace_key: str | None) -> dict:
        headers = dict(self.headers)
        if workspace_key:
            headers["LIGHTRAG-WORKSPACE"] = workspace_key
        return headers

    def get_resquest_body(
        self,
        query: str,
        conversation_history=None,
        history_turns=10,
    ):
        return {
            "query": query,
            "mode": "hybrid",
            "only_need_context": False,
            "only_need_prompt": False,
            "response_type": "Multiple Paragraphs",
            "top_k": 15,
            "chunk_top_k": 8,
            "max_entity_tokens": 2000,
            "max_relation_tokens": 2000,
            "max_total_tokens": 8000,
            "conversation_history": [] if conversation_history is None else conversation_history,
            "history_turns": history_turns,
            "ids": [],
            "user_prompt": "",
            "enable_rerank": True,
        }

    def query(
        self,
        query: str,
        conversation_history=None,
        history_turns=10,
        workspace_key: str | None = None,
    ):
        query_url = f"{self.url}/query"
        param = self.get_resquest_body(query, conversation_history, history_turns)
        res = requests.post(
            query_url,
            json=param,
            headers=self._workspace_headers(workspace_key),
            timeout=self.timeout,
        )
        res.raise_for_status()
        return res.json()

    def query_stream(
        self,
        query: str,
        conversation_history=None,
        history_turns=10,
        workspace_key: str | None = None,
    ):
        query_url = f"{self.url}/query/stream"
        param = self.get_resquest_body(query, conversation_history, history_turns)
        res = requests.post(
            query_url,
            json=param,
            headers=self._workspace_headers(workspace_key),
            stream=True,
            timeout=self.timeout,
        )
        res.raise_for_status()
        for item in res.iter_lines():
            if not item:
                continue
            content = json.loads(item.decode()).get("response")
            if content:
                yield content

    def insert_text(
        self,
        text: str,
        file_source: str,
        workspace_key: str | None = None,
    ) -> str:
        resp = requests.post(
            f"{self.url}/documents/text",
            json={"text": text, "file_source": file_source},
            headers=self._workspace_headers(workspace_key),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # LightRAG 按 file_source 或内容 hash 去重时返回 duplicated，HTTP 仍为 200
        if data.get("status") == "duplicated":
            raise RuntimeError(
                f"LightRAG 文档重复: {data.get('message', '')}"
            )

        return str(data.get("doc_id") or file_source)

    def get_doc_status(self, doc_id: str, workspace_key: str | None = None) -> str:
        """Query LightRAG for the indexing status of a document.

        LightRAG 的 GET /documents 返回的 id 是内部 content hash，
        与我们的 file_source 不同，因此按 file_path 字段匹配。

        Returns one of: "processed", "processing", "error", "not_found".
        """
        try:
            resp = requests.get(
                f"{self.url}/documents",
                headers=self._workspace_headers(workspace_key),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            statuses = data.get("statuses", {})
            for status, docs in statuses.items():
                if isinstance(docs, list):
                    for d in docs:
                        if d.get("file_path") == doc_id:
                            return status
            return "not_found"
        except Exception:
            return "unknown"

    def upload_document(
        self,
        file_path: str,
        workspace_key: str | None = None,
    ) -> str:
        path = Path(file_path)
        with path.open("rb") as fh:
            resp = requests.post(
                f"{self.url}/documents/upload",
                files={"file": (path.name, fh)},
                headers={
                    k: v
                    for k, v in self._workspace_headers(workspace_key).items()
                    if k.lower() != "content-type"
                },
                timeout=self.timeout,
            )
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("doc_id") or str(path))

    def delete_documents(
        self,
        doc_ids: list[str],
        workspace_key: str | None = None,
        *,
        delete_file: bool = False,
    ) -> None:
        if not doc_ids:
            return
        resp = requests.delete(
            f"{self.url}/documents",
            json={
                "doc_ids": doc_ids,
                "delete_file": delete_file,
                "delete_llm_cache": False,
            },
            headers=self._workspace_headers(workspace_key),
            timeout=self.timeout,
        )
        resp.raise_for_status()

    def delete_by_file_sources(
        self,
        file_sources: list[str],
        workspace_key: str | None = None,
    ) -> None:
        """按 file_path 查找 LightRAG 内部 ID 后删除。

        LightRAG 的 DELETE /documents 只接受内部 hash ID，
        而我们的 rag_doc_id 存储的是 file_source，
        所以需要先查 GET /documents 找到映射关系再调用删除。
        """
        if not file_sources:
            return

        # 1. 查询所有文档，按 file_path 收集内部 ID
        resp = requests.get(
            f"{self.url}/documents",
            headers=self._workspace_headers(workspace_key),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        ids_to_delete = []
        for status, docs in data.get("statuses", {}).items():
            if isinstance(docs, list):
                for d in docs:
                    if d.get("file_path") in file_sources:
                        ids_to_delete.append(d["id"])

        # 2. 用内部 ID 调用删除
        if ids_to_delete:
            self.delete_documents(ids_to_delete, workspace_key)
