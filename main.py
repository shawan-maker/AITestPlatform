import sys
print(f"[DEBUG] Python executable: {sys.executable}")
print(f"[DEBUG] Python version: {sys.version}")
print(f"[DEBUG] sys.path: {sys.path[:3]}...")

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from service.core.config import API_V1_PREFIX, APP_TITLE, APP_VERSION
from service.core.database import close_db, init_db
from service.core.exceptions import AppException
from service.core.redis import close_redis
from service.core.response import success
from service.router import api_router
from service.user.bootstrap import ensure_default_super_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # auto_migrate 已禁用：表结构由 Aerich 手动管理（python scripts/db_manage.py upgrade）
    await ensure_default_super_admin()
    # 清理服务重启前遗留的 running 状态会话
    from service.ai_generation.session_lifecycle import SessionLifecycleService
    await SessionLifecycleService.cleanup_stale_sessions()
    yield
    await close_redis()
    await close_db()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)
app.include_router(api_router, prefix=API_V1_PREFIX)


# ===== ORM 健康诊断中间件 =====
@app.middleware("http")
async def orm_health_check_middleware(request: Request, call_next):
    """在每个请求前后检查 ORM 模型字段完整性，发现损坏立即记录"""
    from service.ai_generation.agent_stream import AgentStreamService
    path = request.url.path

    # 只检查关键 API 路径，避免过多日志
    if any(kw in path for kw in ['/auth/verify', '/projects/', '/sessions', '/messages', '/suites', '/environments']):
        diag_before = AgentStreamService._diagnose_orm_health()
        if 'is_deleted=False' in diag_before or 'gen_type=False' in diag_before or 'apps=EMPTY' in diag_before:
            print(f"[ORM-DIAG] ⚠️ ORM 已损坏! path={path} BEFORE: {diag_before}", flush=True)
        elif '/sessions/' in path or '/messages' in path:
            print(f"[ORM-DIAG] ✅ path={path} BEFORE: {diag_before}", flush=True)

    response = await call_next(request)
    return response


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.code if 400 <= exc.code < 600 else 400,
        content={"code": exc.code, "message": exc.message, "data": exc.data},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0].get("msg", "请求参数校验失败") if errors else "请求参数校验失败"
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": message, "data": errors},
    )


@app.get("/health")
async def health_check():
    return success(data={"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
