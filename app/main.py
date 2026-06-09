from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.articles import router as articles_router
from app.api.categories import router as categories_router
from app.api.comments import router as comments_router
from app.api.feeds import router as feeds_router
from app.api.search import router as search_router
from app.api.seo import router as seo_router
from app.api.subscriptions import router as subscriptions_router
from app.api.tags import router as tags_router
from app.cache import close_redis
from app.config import get_settings
from app.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        from app.search import init_index
        await init_index()
    except Exception:
        pass
    yield
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A modern blog API built with FastAPI",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_prefix = settings.api_prefix

    app.include_router(articles_router, prefix=api_prefix)
    app.include_router(tags_router, prefix=api_prefix)
    app.include_router(categories_router, prefix=api_prefix)
    app.include_router(comments_router, prefix=api_prefix)
    app.include_router(subscriptions_router, prefix=api_prefix)
    app.include_router(search_router, prefix=api_prefix)

    app.include_router(feeds_router)
    app.include_router(seo_router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
