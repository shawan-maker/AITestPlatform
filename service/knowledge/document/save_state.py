from dataclasses import dataclass

from service.api_test.interface.models import ApiInterface
from service.core.enums import IndexStatus, KnowledgeDocType, ParseStatus
from service.functional_test.requirement.models import RequirementCandidate, RequirementDoc
from service.knowledge.document.import_marker import is_interfaces_imported
from service.knowledge.document.models import KnowledgeDocument, KnowledgeDocumentVersion


def _enum_value(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


@dataclass(frozen=True)
class VersionSaveState:
    requirement_saved: bool = False
    can_save_requirement: bool = False
    interfaces_saved: bool = False
    can_save_interfaces: bool = False


async def compute_version_save_state(
    document: KnowledgeDocument,
    version: KnowledgeDocumentVersion,
) -> VersionSaveState:
    requirement_saved = False
    can_save_requirement = False
    interfaces_saved = False
    can_save_interfaces = False

    if document.doc_type == KnowledgeDocType.requirement:
        requirement_saved = await RequirementDoc.filter(
            source_document_id=document.id,
            source_document_version_id=version.id,
        ).exists()
        has_candidate = await RequirementCandidate.filter(
            source_document_id=document.id,
            source_document_version_id=version.id,
        ).exists()
        can_save_requirement = (
            not requirement_saved
            and has_candidate
            and _enum_value(version.index_status) == IndexStatus.indexed.value
        )

    if document.doc_type == KnowledgeDocType.api_doc:
        if _enum_value(version.parse_status) == ParseStatus.parsed.value:
            interfaces_saved = is_interfaces_imported(version.parse_result_path)
            if not interfaces_saved:
                interfaces_saved = await ApiInterface.filter(
                    source_document_id=document.id,
                    source_document_version_id=version.id,
                ).exists()
            can_save_interfaces = not interfaces_saved

    return VersionSaveState(
        requirement_saved=requirement_saved,
        can_save_requirement=can_save_requirement,
        interfaces_saved=interfaces_saved,
        can_save_interfaces=can_save_interfaces,
    )
