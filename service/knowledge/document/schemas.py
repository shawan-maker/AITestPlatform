from datetime import datetime

from pydantic import BaseModel, Field

from service.core.enums import IndexStatus, KnowledgeDocType, ParseMode
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
    index_error: str | None
    file_expired: bool
    created_by_id: int | None
    created_by_username: str | None
    created_at: datetime


class KnowledgeDocumentBrief(BaseModel):
    id: int
    project_id: int
    project_name: str
    title: str
    doc_type: KnowledgeDocType
    parse_mode: ParseMode
    version_label: str | None
    index_status: IndexStatus | None
    updated_at: datetime
    updated_by_username: str | None


class KnowledgeDocumentDetail(KnowledgeDocumentBrief):
    module_id: int | None
    workspace_id: int
    current_version: KnowledgeVersionBrief | None
    created_at: datetime


PaginatedKnowledgeDocuments = Paginated[KnowledgeDocumentBrief]
PaginatedKnowledgeVersions = Paginated[KnowledgeVersionBrief]
