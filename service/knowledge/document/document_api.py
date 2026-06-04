from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from service.core.config import MAX_UPLOAD_BYTES
from service.core.deps import get_current_active_user, require_project_editor
from service.core.enums import IndexStatus, KnowledgeDocType, ParseMode
from service.core.exceptions import AppException
from service.core.response import success
from service.functional_test.requirement.candidate_service import CandidateService
from service.knowledge.document.document_service import DocumentService
from service.knowledge.document.permissions import ensure_document_editor
from service.knowledge.document.schemas import KnowledgeDocumentListQuery
from service.knowledge.document.version_service import VersionService
from service.knowledge.rules.file_rules import FileRules, sha256_hex
from service.user.models import User

router = APIRouter()


def get_document_list_query(
    project_id: int | None = Query(None, ge=1),
    title: str | None = Query(None, description="文档名称模糊搜索"),
    project_name: str | None = Query(None, description="项目名称模糊搜索"),
    doc_type: KnowledgeDocType | None = Query(None),
    index_status: str | None = Query(None),
    parse_mode: ParseMode | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> KnowledgeDocumentListQuery:
    parsed_index_status = IndexStatus(index_status) if index_status is not None else None
    return KnowledgeDocumentListQuery(
        project_id=project_id,
        title=title,
        project_name=project_name,
        doc_type=doc_type,
        index_status=parsed_index_status,
        parse_mode=parse_mode,
        page=page,
        page_size=page_size,
    )


@router.post("/documents", summary="上传知识库文档")
async def upload_document(
    project_id: int = Query(..., ge=1),
    title: str = Form(..., description="文档名称"),
    doc_type: KnowledgeDocType = Form(...),
    parse_mode: ParseMode = Form(...),
    module_id: int | None = Form(None),
    file: UploadFile = File(...),
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    content = await file.read()
    result = await DocumentService.create(
        user,
        project_id,
        title=title,
        doc_type=doc_type,
        parse_mode=parse_mode,
        module_id=module_id,
        file_name=file.filename or "unnamed",
        content=content,
        mime_type=file.content_type,
    )
    return success(data=result, message="文档上传成功")


@router.get("/documents", summary="知识库文档列表")
async def list_documents(
    query: KnowledgeDocumentListQuery = Depends(get_document_list_query),
    user: User = Depends(get_current_active_user),
):
    data = await DocumentService.list_documents(user, query)
    return success(data=data)


@router.get("/documents/{document_id}", summary="知识库文档详情")
async def get_document(
    document_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DocumentService.get_detail(user, document_id)
    return success(data=data.model_dump(mode="json"))


@router.get("/documents/{document_id}/requirement-candidate", summary="当前版本需求候选")
async def get_requirement_candidate(
    document_id: int,
    version_id: int | None = Query(None, ge=1),
    user: User = Depends(get_current_active_user),
):
    data = await CandidateService.get_for_document_version(
        user, document_id, version_id=version_id
    )
    return success(data=data)


@router.get(
    "/documents/{document_id}/versions/{version_id}/text-preview",
    summary="版本文档全文预览",
)
async def get_version_text_preview(
    document_id: int,
    version_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DocumentService.get_version_text_preview(
        user, document_id, version_id=version_id
    )
    return success(data=data)


@router.post("/documents/{document_id}/versions", summary="重新上传文档")
async def upload_document_version(
    document_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
):
    document = await ensure_document_editor(document_id, user)
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise AppException(f"文件大小超过限制 {MAX_UPLOAD_BYTES} 字节", 400)
    FileRules.validate_upload(
        file_name=file.filename or "unnamed",
        content=content,
        doc_type=document.doc_type,
        parse_mode=document.parse_mode,
    )
    version = await VersionService.create_new_version(
        user,
        document_id,
        file_name=file.filename or "unnamed",
        content=content,
        mime_type=file.content_type,
        file_hash=sha256_hex(content),
    )
    brief = await VersionService._to_brief(version)
    return success(data=brief, message="新版本上传成功，等待索引")


@router.get("/documents/{document_id}/versions", summary="历史版本列表")
async def list_document_versions(
    document_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    data = await VersionService.list_versions(
        user, document_id, page=page, page_size=page_size
    )
    return success(data=data)


@router.get("/documents/{document_id}/download", summary="下载当前版本")
async def download_current_document(
    document_id: int,
    user: User = Depends(get_current_active_user),
):
    version, path = await VersionService.resolve_download_path(user, document_id)
    return FileResponse(
        path=path,
        filename=version.file_name,
        media_type=version.mime_type or "application/octet-stream",
    )


@router.get(
    "/documents/{document_id}/versions/{version_id}/download",
    summary="下载指定版本",
)
async def download_document_version(
    document_id: int,
    version_id: int,
    user: User = Depends(get_current_active_user),
):
    version, path = await VersionService.resolve_download_path(
        user, document_id, version_id=version_id
    )
    return FileResponse(
        path=path,
        filename=version.file_name,
        media_type=version.mime_type or "application/octet-stream",
    )


@router.get(
    "/documents/{document_id}/versions/{version_id}/parsed-interfaces",
    summary="版本解析接口列表（只读）",
)
async def get_parsed_interfaces(
    document_id: int,
    version_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DocumentService.get_version_parsed_interfaces(
        user, document_id, version_id
    )
    return success(data=data.model_dump(mode="json"))


@router.post("/documents/{document_id}/reindex", summary="重新索引当前版本")
async def reindex_document(
    document_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await VersionService.trigger_reindex(user, document_id)
    return success(data=data, message="已提交重新索引")


@router.delete("/documents/{document_id}", summary="删除知识库文档")
async def delete_document(
    document_id: int,
    user: User = Depends(get_current_active_user),
):
    await DocumentService.delete(user, document_id)
    return success(message="知识库文档已删除")
