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
    yield
    await close_redis()
    await close_db()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)
app.include_router(api_router, prefix=API_V1_PREFIX)


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
