"""测试环境管理模块 - file/schemas

请求/响应 Schema 定义
"""
from datetime import datetime

from pydantic import BaseModel, Field

from service.core.pagination import Paginated


class UploadedFileBrief(BaseModel):
    """uploaded文件brief"""
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
    """uploaded文件pathresolved"""
    absolute_path: str
    file_name: str
    storage_key: str


# case_payload.request.files 存储引用，执行前由 FileResolver 解析为 path/filename：
# {"avatar": {"uploaded_file_id": 12}}


class UploadedFileBatchDeleteRequest(BaseModel):
    """uploaded文件批量操作删除请求"""
    file_ids: list[int] = Field(..., min_length=1, max_length=50)


class UploadedFileBatchDeleteFailure(BaseModel):
    """uploaded文件批量操作删除failure"""
    file_id: int
    message: str


class UploadedFileBatchDeleteResult(BaseModel):
    """uploaded文件批量操作删除结果"""
    deleted_ids: list[int]
    failures: list[UploadedFileBatchDeleteFailure]
