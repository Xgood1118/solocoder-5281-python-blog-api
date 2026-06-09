from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.feeds import generate_atom_feed, generate_rss_feed
from app.models import Article, ArticleStatus
from sqlalchemy import desc, select

router = APIRouter(tags=["feeds"])


@router.get("/feed")
@router.get("/feed/rss")
async def rss_feed(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.published_at), desc(Article.created_at))
        .limit(20)
    )
    articles = list(result.scalars().all())

    content = generate_rss_feed(articles)
    return Response(content=content, media_type="application/rss+xml; charset=utf-8")


@router.get("/feed/atom")
async def atom_feed(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.published_at), desc(Article.created_at))
        .limit(20)
    )
    articles = list(result.scalars().all())

    content = generate_atom_feed(articles)
    return Response(content=content, media_type="application/atom+xml; charset=utf-8")
