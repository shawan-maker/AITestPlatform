"""Shared helpers for AI generation (prompt formatting, hashing)."""

from __future__ import annotations

import hashlib
import os

from service.core.exceptions import AppException
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion
from service.knowledge.document.storage import KnowledgeStorage


def format_user_prompt_section(user_prompt: str | None) -> str:
    """Return markdown section for user prompt, or empty string when absent."""
    if not user_prompt or not user_prompt.strip():
        return ""
    return f"\n## 用户附加要求\n{user_prompt.strip()}\n"


def build_default_additional_info() -> dict[str, str]:
    """Default additional_info for API runcase generation (configurable notice)."""
    from service.core import config as core_config

    return {"notice": core_config.AI_GENERATION_DEFAULT_NOTICE}


def is_llm_configured() -> bool:
    return bool(os.getenv("LLM_BINDING_API_KEY"))


def functional_gen_use_mock() -> bool:
    return os.getenv("FUNCTIONAL_GEN_MOCK") == "1"


def api_test_gen_use_mock() -> bool:
    return os.getenv("API_TEST_GEN_MOCK") == "1"


LLM_NOT_CONFIGURED_MSG = "未配置 LLM_BINDING_API_KEY，无法执行 AI 生成"


SESSION_TITLE_PROMPT = """请根据以下对话的第一条用户消息，用不超过15个中文汉字概括该对话的主题。
仅输出概括文字，不要任何解释或标点。

用户消息：{user_first_message}

概括："""


def compute_prompt_hash(source_text: str, user_prompt: str | None) -> str:
    """Return sha256 hex digest of source text combined with optional user prompt."""
    parts = [source_text]
    if user_prompt and user_prompt.strip():
        parts.append(user_prompt.strip())
    combined = "\n".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


async def load_knowledge_document_text(document_id: int, project_id: int) -> str:
    """Load indexed knowledge document text for AI generation."""
    doc = await KnowledgeDocument.get_or_none(id=document_id, project_id=project_id)
    if doc is None:
        raise AppException("知识库文档不存在", 404)
    if not doc.current_version_id:
        raise AppException("知识库文档无有效版本", 400)

    version = await KnowledgeDocumentVersion.get_or_none(
        id=doc.current_version_id,
        document_id=document_id,
    )
    if version is None:
        raise AppException("知识库文档版本不存在", 404)

    if not version.file_expired and version.file_path:
        path = KnowledgeStorage.absolute_path(version.file_path)
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError as exc:
                raise AppException(f"读取知识库文档失败: {exc}", 500) from exc
            if text:
                return text

    raise AppException("知识库文档内容为空", 400)
