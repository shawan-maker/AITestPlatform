from datetime import datetime

from pydantic import BaseModel

from service.core.pagination import Paginated


class UploadedFileBrief(BaseModel):
    id: int
    project_id: int
    file_name: str
    file_size: int
    mime_type: str | None
    uploaded_by_id: int | None
    created_at: datetime
    updated_at: datetime


PaginatedUploadedFiles = Paginated[UploadedFileBrief]


class UploadedFilePathResolved(BaseModel):
    absolute_path: str
    file_name: str
    storage_key: str


# case_payload.request.files 存储引用，执行前由 FileResolver 解析为 path/filename：
# {"avatar": {"uploaded_file_id": 12}}
