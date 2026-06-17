from fastapi import APIRouter, Depends, Query

from service.api_test.debug.schemas import DebugRunRequest, DebugTemplateSaveRequest
from service.api_test.debug.template_service import DebugTemplateService
from service.api_test.shared.runner_gateway import _make_json_safe
from service.core.deps import get_current_active_user
from service.core.pagination import paginate
from service.core.response import success
from service.test_execution.models import ApiCaseRunRecord
from service.user.models import User

router = APIRouter(tags=["接口测试-调试"])


@router.get("/interfaces/{interface_id}/debug-template", summary="读取调试模板")
async def get_debug_template(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DebugTemplateService.get_template(user, interface_id)
    return success(data=data)


@router.put("/interfaces/{interface_id}/debug-template", summary="保存调试模板")
async def save_debug_template(
    interface_id: int,
    body: DebugTemplateSaveRequest,
    user: User = Depends(get_current_active_user),
):
    data = await DebugTemplateService.save_template(user, interface_id, body)
    return success(data=data, message="调试模板已保存")


@router.post(
    "/interfaces/{interface_id}/debug-template/fill-from-doc",
    summary="从文档填充调试模板",
)
async def fill_debug_template(
    interface_id: int,
    user: User = Depends(get_current_active_user),
):
    data = await DebugTemplateService.fill_from_doc(user, interface_id)
    return success(data=data, message="模板已填充")


@router.post("/interfaces/{interface_id}/debug-run", summary="接口调试运行")
async def debug_run_interface(
    interface_id: int,
    body: DebugRunRequest,
    user: User = Depends(get_current_active_user),
):
    record = await DebugTemplateService.debug_run(
        user,
        interface_id,
        environment_id=body.environment_id,
        payload=body.payload,
        file_id=body.file_id,
    )
    
    # 构造详细的返回结果
    base_data = {
        'run_record_id': record.id,
        'status': record.status.value if hasattr(record.status, 'value') else str(record.status),
        'duration_ms': record.duration_ms,
        'executor': user.username if user else None,
        'error_message': record.error_message,
    }
    
    # 如果有api_requests_info（包含详细的调试信息），合并到返回数据中
    if record.api_requests_info and isinstance(record.api_requests_info, dict):
        # 提取引擎返回的详细信息
        debug_detail = record.api_requests_info.get('_debug_detail', {})
        
        # 合并所有信息到返回结果中
        base_data.update({
            **debug_detail,
            # 确保基本信息优先级最高
            'status': debug_detail.get('status', base_data['status']),
            'duration_ms': debug_detail.get('duration_ms', base_data['duration_ms']),
            'error_message': debug_detail.get('error_message', base_data['error_message']) or base_data['error_message'],
        })
    
    return success(data=base_data)


@router.get("/interfaces/{interface_id}/debug-records", summary="接口调试运行历史")
async def list_debug_records(
    interface_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
):
    # 获取接口名称
    from service.api_test.models import ApiInterface
    iface = await ApiInterface.get_or_none(id=interface_id)
    iface_name = (iface.summary or iface.name) if iface else None

    qs = (
        ApiCaseRunRecord.filter(interface_id=interface_id, run_type="debug")
        .order_by("-created_at")
        .prefetch_related("triggered_by")
    )
    total, items = await paginate(qs, page, page_size)
    records = []
    for r in items:
        triggered_by_name = ""
        if r.triggered_by:
            triggered_by_name = r.triggered_by.username if hasattr(r.triggered_by, 'username') else ""
        records.append({
            "id": r.id,
            "case_name": r.case_name or "",
            "interface_name": iface_name,
            "status": r.status.value if hasattr(r.status, 'value') else str(r.status),
            "duration_ms": r.duration_ms,
            "error_message": r.error_message,
            "triggered_by_username": triggered_by_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "api_requests_info": _make_json_safe(r.api_requests_info) if r.api_requests_info else None,
        })
    return success(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": records,
    })
