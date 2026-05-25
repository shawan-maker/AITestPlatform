import json
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile

from service.core.deps import get_current_active_user, require_project_editor, require_project_viewer
from service.core.exceptions import AppException
from service.core.response import success
from service.test_environment.variable.import_export_service import ImportExportService
from service.test_environment.variable.schemas import EnvironmentExportBundle, EnvironmentImportRequest
from service.user.models import User

router = APIRouter(tags=["环境-导入导出"])


@router.get("/environments/{environment_id}/export", summary="导出变量文件")
async def export_environment(
    environment_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await ImportExportService.export_environment(user, environment_id)
    return success(data=data)


@router.post("/environments/import", summary="导入变量文件")
async def import_environment(
    data: EnvironmentImportRequest,
    project_id: int = Query(..., ge=1),
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    result = await ImportExportService.import_environment(user, project_id, data)
    return success(data=result, message="导入成功")


@router.post("/environments/import-file", summary="上传 JSON 文件导入变量文件")
async def import_environment_file(
    project_id: int = Query(..., ge=1),
    overwrite: bool = Query(False),
    import_mode: Literal["reference", "embed"] = Query("embed"),
    file: UploadFile = File(...),
    _: tuple = Depends(require_project_editor),
    user: User = Depends(get_current_active_user),
):
    raw = await file.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppException("无效的 JSON 文件", 400) from exc
    if isinstance(payload, dict) and "bundle" in payload:
        request = EnvironmentImportRequest(**payload)
    else:
        request = EnvironmentImportRequest(
            bundle=EnvironmentExportBundle(**payload),
            overwrite=overwrite,
            import_mode=import_mode,
        )
    if request.import_mode is None:
        request.import_mode = import_mode
    if not request.overwrite:
        request.overwrite = overwrite
    result = await ImportExportService.import_environment(user, project_id, request)
    return success(data=result, message="导入成功")
