"""FastAPI 应用工厂（11.1.1）。

目录结构、路由注册、依赖注入、中间件。
可独立运行，也可通过 ASGI 挂载到 Django 项目。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import check_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时
    db_ok = await check_db_connection()
    if not db_ok:
        import logging
        logging.getLogger("fastapi").warning("数据库连接失败，请检查配置")
    yield


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(
        title=settings.app_name,
        description="i·Space Doc — 轻量级知识文档管理平台",
        version="2.0.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    from .routers import health, auth as auth_router, documents
    app.include_router(health.router, tags=["Health"])
    app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(documents.router, prefix="/api", tags=["Documents"])

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        return JSONResponse(status_code=500, content={"error": "服务器内部错误"})

    return app


# 应用实例
app = create_app()
