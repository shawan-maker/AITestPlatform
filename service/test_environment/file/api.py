from fastapi import APIRouter, Depends, File, Query, UploadFile

from service.core.deps import get_current_active_user, require_project_editor, require_project_viewer
from service.core.response import success
from service.test_environment.file.service import UploadedFileService
from service.user.models import User

router = APIRouter(prefix="/uploaded-files", tags=["环境-上传文件"])


@router.get("", summary="上传文件列表")
async def list_uploaded_files(
    project_id: int = Query(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: tuple = Depends(require_project_viewer),
    user: User = Depends(get_current_active_user),
):
    data = await UploadedFileService.list_files(
        user, project_id, page=page, page_size=page_size
    )
    return success(data=data)


@router.post("", summary="上传文件")
async def upload_file(
    project_id: int = Query(..., ge=1),
    file: UploadFile = File(...),
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    content = await file.read()
    result = await UploadedFileService.upload(
        user,
        project_id,
        file_name=file.filename or "unnamed",
        content=content,
        mime_type=file.content_type,
    )
    return success(data=result, message="文件上传成功")


@router.delete("/{file_id}", summary="软删除文件")
async def delete_uploaded_file(
    file_id: int,
    user: User = Depends(get_current_active_user),
):
    await UploadedFileService.soft_delete(user, file_id)
    return success(message="文件已删除")


@router.get("/{file_id}/resolve-path", summary="解析上传文件绝对路径")
async def resolve_uploaded_file_path(
    file_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await UploadedFileService.resolve_path(user, file_id)
    return success(data=data)


@router.get("/{file_id}/download", summary="下载文件")
async def download_file(
    file_id: int,
    user: User = Depends(get_current_active_user),
):
    return await UploadedFileService.download(user, file_id)
