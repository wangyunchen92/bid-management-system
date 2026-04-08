"""
招投标管理平台 - FastAPI 应用入口
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import close_db, init_db, async_session_factory
from app.common.exceptions import (
    BusinessException,
    NotFoundException,
    ForbiddenException,
    UnauthorizedException,
)
from app.common.response import ResponseModel

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动中...")
    await init_db()
    await _init_base_data()
    yield
    await close_db()
    logger.info("应用已关闭")


app = FastAPI(
    title="招投标管理平台",
    description="招投标管理平台后端 API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(status_code=200, content=ResponseModel(code=exc.code, message=exc.message, data=None).model_dump())


@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(status_code=404, content=ResponseModel(code=404, message=exc.message, data=None).model_dump())


@app.exception_handler(ForbiddenException)
async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(status_code=403, content=ResponseModel(code=403, message=exc.message, data=None).model_dump())


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(status_code=401, content=ResponseModel(code=401, message=exc.message, data=None).model_dump())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content=ResponseModel(code=500, message="服务器内部错误", data=None).model_dump())


# 注册路由
from app.routers import auth

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证管理"])


@app.get("/api/health", tags=["健康检查"])
async def health_check():
    return ResponseModel(code=200, message="ok", data={"status": "healthy"})


async def _init_base_data():
    from sqlalchemy import select
    from app.models.system import SysUser
    from app.common.security import hash_password

    async with async_session_factory() as session:
        result = await session.execute(
            select(SysUser).where(SysUser.username == "admin")
        )
        if not result.scalar_one_or_none():
            admin = SysUser(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="系统管理员",
                phone="13800000000",
                role="SUPER_ADMIN",
                status=1,
            )
            session.add(admin)
            await session.commit()
            logger.info("默认管理员 admin/admin123 已创建")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.APP_DEBUG)
