from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from service.core.config import API_V1_PREFIX, APP_TITLE, APP_VERSION
from service.core.database import close_db, init_db
from service.core.exceptions import AppException
from service.core.response import success
from service.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 表结构由 Aerich 管理，部署前执行: python scripts/db_manage.py upgrade
    await init_db()
    yield
    await close_db()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)
app.include_router(api_router, prefix=API_V1_PREFIX)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.code if 400 <= exc.code < 600 else 400,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


@app.get("/health")
async def health_check():
    return success(data={"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
