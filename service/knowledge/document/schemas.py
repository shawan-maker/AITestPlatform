from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import IndexStatus, KnowledgeDocType, ParseMode, ParseStatus
from service.core.pagination import Paginated


class KnowledgeDocumentListQuery(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    title: str | None = None
    project_name: str | None = None
    doc_type: KnowledgeDocType | None = None
    index_status: IndexStatus | None = None
    parse_mode: ParseMode | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class KnowledgeVersionBrief(BaseModel):
    id: int
    document_id: int
    version_label: str
    version_seq: int
    file_name: str
    file_size: int | None
    mime_type: str | None
    index_status: IndexStatus
    parse_status: ParseStatus | None = None
    index_error: str | None
    file_expired: bool
    created_by_id: int | None
    created_by_username: str | None
    created_at: datetime


class KnowledgeDocumentBrief(BaseModel):
    id: int
    project_id: int
    project_name: str
    module_id: int | None = None
    module_name: str | None = None
    title: str
    doc_type: KnowledgeDocType
    parse_mode: ParseMode
    version_label: str | None
    current_version_id: int | None = None
    index_status: IndexStatus | None
    parse_status: ParseStatus | None = None
    interfaces_saved: bool = False
    can_save_interfaces: bool = False
    updated_at: datetime
    updated_by_username: str | None


class ParsedInterfaceItem(BaseModel):
    method: str
    path: str
    summary: str | None = None
    module_name: str | None = None
    catalog_path: str | None = None


class KnowledgeDocumentDetail(KnowledgeDocumentBrief):
    workspace_id: int
    current_version: KnowledgeVersionBrief | None
    created_at: datetime
    parsed_interfaces: list[ParsedInterfaceItem] = Field(default_factory=list)


PaginatedKnowledgeDocuments = Paginated[KnowledgeDocumentBrief]
PaginatedKnowledgeVersions = Paginated[KnowledgeVersionBrief]


class ParsedInterfaceListResult(BaseModel):
    document_id: int
    version_id: int
    items: list[ParsedInterfaceItem]
