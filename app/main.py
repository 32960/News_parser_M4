from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import router
from app.db import engine, init_db
from app.log_config import configure_logs

APP_DESCRIPTION = """
AI news post generator for Telegram.

## Typical flow
1. **Sources** — create a site or Telegram source (`POST /api/sources/`)
2. **Collect** — `POST /api/parse/` (HTTP 202 + `task_id`), then check `GET /api/news/`
3. **Generate** — automatic after new news, or manual `POST /api/generate/` (202 + `post_id`)
4. **Publish** — on schedule (UTC `:00` / `:30`) or manual `POST /api/posts/{id}/publish/`

## Useful response codes
- **200** — read/update OK; also: publish when post is already `published`
- **201** — source created
- **202** — Celery job accepted (`parse` / `generate` / `publish`)
- **204** — source deleted
- **404** — unknown id
- **409** — conflict (e.g. delete source with news, generate for disabled source, publish without text)
- **422** — invalid body or unsupported site URL

Supported site URLs:
- `https://habr.com/ru/rss/articles/`
- `https://www.theverge.com/rss/index.xml`
"""

OPENAPI_TAGS = [
    {
        "name": "Sources",
        "description": "Add, update, enable/disable and delete news sources",
    },
    {
        "name": "News",
        "description": "Collected news items from enabled sources",
    },
    {
        "name": "Posts",
        "description": "AI-generated posts, statuses and manual publish",
    },
    {
        "name": "Jobs",
        "description": "Background jobs: collection and AI generation",
    },
]


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
        description=APP_DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )
    application.include_router(router)
    return application


app = create_app()
