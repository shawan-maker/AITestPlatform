from fastapi import APIRouter

router = APIRouter(prefix="/environments", tags=["测试环境"])

# TODO: 环境、配置、数据库连接、快照 CRUD 等接口
