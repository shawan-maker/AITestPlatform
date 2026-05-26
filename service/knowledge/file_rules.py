import hashlib
import json
from pathlib import Path

import yaml

from service.core.config import KNOWLEDGE_UPLOAD_ROOT
from service.core.enums import IndexStatus, KnowledgeDocType, ParseMode
from service.core.exceptions import AppException

REQUIREMENT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".doc"}
API_AI_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".doc"}
API_SPEC_EXTENSIONS = {".json", ".yaml", ".yml"}


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def detect_api_spec_kind(content: bytes) -> str | None:
    """返回 swagger / openapi / None。"""
    text = content.decode("utf-8", errors="ignore").strip()
    if not text:
        return None
    try:
        if text.startswith("{"):
            data = json.loads(text)
        else:
            data = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    if "swagger" in data:
        return "swagger"
    if "openapi" in data:
        return "openapi"
    return None


class FileRules:
    @classmethod
    def validate_upload(
        cls,
        *,
        file_name: str,
        content: bytes,
        doc_type: KnowledgeDocType,
        parse_mode: ParseMode,
    ) -> None:
        ext = Path(file_name).suffix.lower()
        if doc_type == KnowledgeDocType.requirement:
            if parse_mode != ParseMode.ai:
                raise AppException("功能需求文档仅支持 AI 解析", 400)
            if ext not in REQUIREMENT_EXTENSIONS:
                raise AppException(
                    f"功能需求文档不支持该文件类型: {ext or '(无扩展名)'}", 400
                )
            return

        if doc_type == KnowledgeDocType.api_doc:
            if parse_mode == ParseMode.ai:
                if ext not in API_AI_EXTENSIONS | API_SPEC_EXTENSIONS:
                    raise AppException(
                        f"接口文档不支持该文件类型: {ext or '(无扩展名)'}", 400
                    )
                return
            if parse_mode == ParseMode.swagger:
                if ext not in API_SPEC_EXTENSIONS:
                    raise AppException("Swagger 解析仅支持 .json/.yaml/.yml", 400)
                if detect_api_spec_kind(content) != "swagger":
                    raise AppException("文件内容不是有效的 Swagger 2.0 规范", 400)
                return
            if parse_mode == ParseMode.openapi:
                if ext not in API_SPEC_EXTENSIONS:
                    raise AppException("OpenAPI 解析仅支持 .json/.yaml/.yml", 400)
                if detect_api_spec_kind(content) != "openapi":
                    raise AppException("文件内容不是有效的 OpenAPI 3.x 规范", 400)
                return

        raise AppException("不支持的文档类型", 400)

    @staticmethod
    def initial_index_status(doc_type: KnowledgeDocType, parse_mode: ParseMode) -> IndexStatus:
        if doc_type == KnowledgeDocType.api_doc and parse_mode in (
            ParseMode.swagger,
            ParseMode.openapi,
        ):
            return IndexStatus.pending
        return IndexStatus.pending
