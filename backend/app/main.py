"""创建 FastAPI 应用，由 Uvicorn 命令或 IDE 运行配置负责启动服务。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.config import Settings
from app.database import create_database_engine
from app.documents.routes import router as documents_router
from app.errors import handle_database_error
from app.health.routes import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """将连接池限制在一个应用生命周期内，测试可显式传入临时库配置。"""
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(configuration)
        application.state.database_engine = engine
        try:
            yield
        finally:
            engine.dispose()
            engine.dispose()

    application = FastAPI(
        title="私人工作站 API",
        description="个人研发工作记录与 Markdown 文档管理接口。",
        version=__version__,
        lifespan=lifespan,
    )
    application.add_exception_handler(SQLAlchemyError, handle_database_error)
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(documents_router, prefix="/api/v1")
    return application


app = create_app()
