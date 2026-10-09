from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import router
from app.db import engine, init_db
from app.log_config import configure_logs


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        configure_logs()
        init_db()
        yield
    finally:
        engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="AINEWS",
        description=(
            "AI news post generator for Telegram. "
            "Manage sources, collect news, generate posts and publish them. "
            "Interactive docs: /docs"
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


app = create_app()
