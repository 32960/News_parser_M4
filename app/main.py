from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    return app

app = create_app()
