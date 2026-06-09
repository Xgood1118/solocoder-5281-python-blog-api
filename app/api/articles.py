from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ArticleCreate,
    ArticleDetail,
    ArticleListResponse,
    ArticleSummary,
    ArticleUpdate,
)
from app.services import article_service
from app.services.cache_service import SingleFlight, get_hot_articles_cached, set_hot_articles_cache
from app.tasks import sync_article_to_search, remove_article_from_search

router = APIRouter(prefix="/articles", tags=["articles"])


def _get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    items, total = await article_service.list_articles(
        db,
        page=page,
        page_size=page_size,
        status=status,
        category_id=category_id,
        tag_id=tag_id,
        search=search,
    )
    total_pages = (total + page_size - 1) // page_size
    return ArticleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/hot", response_model=list[ArticleSummary])
async def get_hot_articles(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    async def _fetch():
        articles = await article_service.get_hot_articles(db, limit=limit)
        data = [
            {
                "id": a.id,
                "title": a.title,
                "slug": a.slug,
                "summary": a.summary,
                "cover_image": a.cover_image,
                "status": a.status,
                "author": a.author,
                "views": a.views,
                "likes": a.likes,
                "comment_count": a.comment_count,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat(),
            }
            for a in articles
        ]
        await set_hot_articles_cache(data)
        return data

    cached = await get_hot_articles_cached()
    if cached:
        return cached

    result = await SingleFlight.execute("hot_articles", _fetch)
    return result


@router.get("/archives")
async def get_archives(
    db: AsyncSession = Depends(get_db),
):
    archives = await article_service.get_archives_by_month(db)
    return {"archives": archives}


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    article = await article_service.get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/slug/{slug}", response_model=ArticleDetail)
async def get_article_by_slug(
    slug: str,
    increment_view: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    article = await article_service.get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if increment_view:
        article.views += 1
        await db.commit()
        await db.refresh(article)
        article = await article_service.get_article_by_slug(db, slug)

    return article


@router.post("", response_model=ArticleDetail, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_data: ArticleCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        article = await article_service.create_article(
            db, article_data, request_ip=_get_request_ip(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(sync_article_to_search, article)

    return article


@router.put("/{article_id}", response_model=ArticleDetail)
async def update_article(
    article_id: int,
    article_data: ArticleUpdate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    article = await article_service.update_article(
        db, article_id, article_data, request_ip=_get_request_ip(request)
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    background_tasks.add_task(sync_article_to_search, article)

    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    success = await article_service.delete_article(
        db, article_id, request_ip=_get_request_ip(request)
    )
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")

    background_tasks.add_task(remove_article_from_search, article_id)

    return None


@router.post("/{article_id}/like")
async def like_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    success = await article_service.increment_likes(db, article_id)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"success": True}
