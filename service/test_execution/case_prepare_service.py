"""测试执行模块 - case_prepare_service

业务逻辑服务
"""
from typing import Any

from service.test_environment.file.resolver import FileResolver


async def prepare_case_payload(
    project_id: int, case_payload: dict[str, Any]
) -> dict[str, Any]:
    """执行前预处理：将 case_payload.request.files 中的 uploaded_file_id 解析为绝对路径。"""
    return await FileResolver.resolve_request_files(project_id, case_payload)
