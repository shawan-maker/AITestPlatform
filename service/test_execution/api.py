from fastapi import APIRouter

router = APIRouter(prefix="/test-execution", tags=["测试执行"])

# TODO: 触发执行、运行记录查询等接口
# 执行前须调用 case_prepare_service.prepare_case_payload 解析 request.files 中的 uploaded_file_id
