"""
AITestPlatform (巧乐AI智能体测试平台) FastAPI 应用入口

启动: python main.py 或 uvicorn main:app --host 0.0.0.0 --port 8000 (端口 8000)
生命周期: 初始化DB → 修补连接池 → 创建默认超管 → 清理遗留AI会话

部署配置（.env）:
    BACKEND_HOST  - 监听地址，默认 127.0.0.1（Nginx 同机部署适用）
    BACKEND_PORT  - 监听端口，默认 8000
    CORS_ORIGINS  - CORS 允许的前端域名，逗号分隔；同域部署留空
    LOG_FILE      - 日志文件路径，留空则仅输出到控制台
"""
import sys
import os

# 将所有输出同时写入控制台和日志文件（可选，由 LOG_FILE 环境变量控制）

class _TeeWriter:
    """同时写入多个流（控制台 + 文件）"""
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass
    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass
    def isatty(self):
        return False
    def fileno(self):
        return self.streams[0].fileno()

# 日志文件配置：从 .env 读取 LOG_FILE，留空则仅输出到控制台
_log_path = os.getenv("LOG_FILE", "").strip()
if _log_path:
    os.makedirs(os.path.dirname(_log_path) or ".", exist_ok=True)
    _log_file = open(_log_path, 'a', encoding='utf-8')
    sys.stdout = _TeeWriter(sys.__stdout__, _log_file)
    sys.stderr = _TeeWriter(sys.__stderr__, _log_file)
else:
    _log_file = None

# 配置日志模块也写入同一文件（仅当 LOG_FILE 配置时）
import logging
if _log_file:
    _file_handler = logging.StreamHandler(_log_file)
    _file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt='%H:%M:%S'))
    logging.getLogger().addHandler(_file_handler)
logging.getLogger().setLevel(logging.DEBUG)

# db_trace logger 同时输出到控制台和文件
_db_trace_logger = logging.getLogger("db_trace")
_console_handler = logging.StreamHandler(sys.__stdout__)
_console_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S'))
_db_trace_logger.addHandler(_console_handler)
if _log_file:
    _db_trace_logger.addHandler(_file_handler)
_db_trace_logger.setLevel(logging.INFO)
_db_trace_logger.propagate = False

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from service.core.settings import API_V1_PREFIX, APP_TITLE, APP_VERSION
from service.core.database import close_db, init_db
from service.core.exceptions import AppException
from service.core.redis import close_redis
from service.core.response import success
from service.router import api_router
from service.user.bootstrap import ensure_default_super_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理: 启动初始化DB/超管/清理会话, 关闭Redis和DB连接"""
    await init_db()

    # ===== 连接池修复：acquire 后冲洗连接，防止残留数据串流 =====
    from tortoise.backends.mysql.client import MySQLClient, PoolConnectionWrapper
    _orig_aenter = PoolConnectionWrapper.__aenter__

    async def _flushing_aenter(self):
        conn = await _orig_aenter(self)
        # 冲洗连接：执行无害查询，清空残留的结果缓冲区
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                await cursor.fetchall()
        except Exception:
            pass
        return conn

    PoolConnectionWrapper.__aenter__ = _flushing_aenter
    # ===== 修复完毕 =====

    # auto_migrate 已禁用：表结构由 Aerich 手动管理（python deploy/scripts/db_manage.py upgrade）
    await ensure_default_super_admin()
    # 清理服务重启前遗留的 running 状态会话
    from service.ai_generation.session_lifecycle import SessionLifecycleService
    await SessionLifecycleService.cleanup_stale_sessions()
    yield
    # Shutdown: 带超时关闭连接，防止活跃 SSE/后台线程导致卡死
    import asyncio as _asyncio
    try:
        await _asyncio.wait_for(close_redis(), timeout=3)
    except Exception:
        pass
    try:
        await _asyncio.wait_for(close_db(), timeout=5)
    except _asyncio.TimeoutError:
        print("[SHUTDOWN] close_db 超时，强制退出", flush=True)
    except Exception:
        pass


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# CORS: 从 .env 的 CORS_ORIGINS 读取允许的前端域名
# 同域 Nginx 部署时留空即可（同源请求不需要 CORS）
# 分域部署时配置如: CORS_ORIGINS=https://frontend.example.com
from fastapi.middleware.cors import CORSMiddleware
from service.core.settings import CORS_ORIGINS as _cors_origins

if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=API_V1_PREFIX)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """全局业务异常处理器: 将 AppException 转换为标准 JSON 响应"""
    return JSONResponse(
        status_code=exc.code if 400 <= exc.code < 600 else 400,
        content={"code": exc.code, "message": exc.message, "data": exc.data},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """全局参数校验异常处理器: 返回 422 和具体校验错误"""
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
    from service.core.settings import BACKEND_HOST, BACKEND_PORT

    uvicorn.run("main:app", host=BACKEND_HOST, port=BACKEND_PORT)
