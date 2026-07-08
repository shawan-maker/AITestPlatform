"""知识库管理模块 - document/save_state

save state
"""
from dataclasses import dataclass
import logging

from service.api_test.interface.models import ApiInterface
from service.core.enums import IndexStatus, ParseStatus
from service.knowledge.document.import_marker import is_interfaces_imported
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VersionSaveState:
    """版本保存state"""
    interfaces_saved: bool = False
    can_save_interfaces: bool = False


async def compute_version_save_state(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
) -> VersionSaveState:
    interfaces_saved = False
    can_save_interfaces = False

    parse_status_val = _enum_value(version.parse_status)
    index_status_val = _enum_value(version.index_status)
    actual_route = _enum_value(getattr(version, 'actual_parse_route', None))

    if document.doc_type == "api_doc":
        # 已完成的结构化解析（Swagger/OpenAPI）
        if parse_status_val == ParseStatus.parsed.value:
            interfaces_saved = is_interfaces_imported(version.parse_result_path)
            if not interfaces_saved:
                interfaces_saved = await ApiInterface.filter(
                    source_document_id=document.id,
                    source_document_version_id=version.id,
                ).exists()
            can_save_interfaces = not interfaces_saved
        # 注意：AI/RAG 解析(indexed) 不产生结构化接口数据，
        # 无法通过"保存接口"功能导入到目录树中，因此 can_save 保持 false
        else:
            pass

    result = VersionSaveState(
        interfaces_saved=interfaces_saved,
        can_save_interfaces=can_save_interfaces,
    )
    return result


def _enum_value(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)
