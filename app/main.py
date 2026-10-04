from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db, engine
from app.log_config import configure_logs
from .api.routers import router

@asynccontextmanager
async  def lifespan(app: FastAPI):
    try:
        configure_logs()
        init_db()
        yield
    finally:
        engine.dispose()


def create_app() -> FastAPI:
    return FastAPI(lifespan=lifespan)

app = create_app()
app.include_router(router)
