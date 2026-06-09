from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Article, ArticleStatus
from app.schemas import ArticleSummary

settings = get_settings()

router = APIRouter(tags=["seo"])


@router.get("/sitemap.xml")
async def sitemap(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED.value)
        .order_by(desc(Article.published_at))
        .limit(50000)
    )
    articles = list(result.scalars().all())

    base_url = settings.site_url

    urls = []
    urls.append({"loc": f"{base_url}/", "changefreq": "daily", "priority": "1.0"})
    urls.append({"loc": f"{base_url}/articles", "changefreq": "daily", "priority": "0.9"})

    for article in articles:
        lastmod = article.updated_at or article.created_at
        urls.append({
            "loc": f"{base_url}/articles/{article.slug}",
            "lastmod": lastmod.strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "0.8",
        })

    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for url in urls:
        sitemap_xml += "  <url>\n"
        sitemap_xml += f"    <loc>{url['loc']}</loc>\n"
        if "lastmod" in url:
            sitemap_xml += f"    <lastmod>{url['lastmod']}</lastmod>\n"
        sitemap_xml += f"    <changefreq>{url['changefreq']}</changefreq>\n"
        sitemap_xml += f"    <priority>{url['priority']}</priority>\n"
        sitemap_xml += "  </url>\n"

    sitemap_xml += "</urlset>"

    return Response(content=sitemap_xml, media_type="application/xml; charset=utf-8")


@router.get("/robots.txt")
async def robots_txt(request: Request):
    base_url = settings.site_url
    content = f"""User-agent: *
Allow: /

Sitemap: {base_url}/sitemap.xml
"""
    return Response(content=content, media_type="text/plain; charset=utf-8")


@router.get("/og/{article_slug}")
async def og_meta(
    article_slug: str,
    db: AsyncSession = Depends(get_db),
):
    from app.services import article_service

    article = await article_service.get_article_by_slug(db, article_slug)
    if not article:
        return {
            "title": settings.site_name,
            "description": settings.site_description,
            "type": "website",
            "url": settings.site_url,
            "image": None,
        }

    return {
        "title": article.seo_title or article.title,
        "description": article.seo_description or article.summary or "",
        "type": "article",
        "url": f"{settings.site_url}/articles/{article.slug}",
        "image": article.og_image or article.cover_image,
        "published_time": article.published_at.isoformat() if article.published_at else None,
        "author": article.author,
        "tags": [tag.name for tag in article.tags],
    }
